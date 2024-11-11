import boto3
import duckdb
import json
import pandas as pd
from bs4 import BeautifulSoup
import logging
import io
import sys

from botocore.exceptions import ClientError

# Log levels are NOTSET, DEBUG, INFO, WARNING, ERROR, CRITIAL
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

brt = boto3.client(service_name="bedrock-runtime")
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
s3 = boto3.client('s3')
input_cost = .000003
output_cost = .000015

def parse_conversation(conversation):
    """
    returns a JSON representation of a conversation passed in by the web UI
    """
    response = []
    soup = BeautifulSoup(conversation, features="lxml")
    lines = soup.find_all("div")
    logging.info('INFO: parse_conversation: The div objects from the input conversation are: \n' + str(lines))
    for line in lines:
        text = line.text
        try:
            if "user: " in text:
                pieces = text.split("ser: ")
                logging.info('INFO: parse_conversation: The pieces from the div are: \n' + str(pieces))
                output = {
                    "role": "user",
                    "content": [{"text": pieces[1]}],
                }
            else:
                pieces = text.split("ssistant: ")
                logging.info('INFO: parse_conversation: The pieces from the div are: \n' + str(pieces))
                output = {
                    "role": "assistant",
                    "content": [{"text": pieces[1]}],
                }
            response.append(output)
        except Exception as e:
            logger.error('ERROR: Unable to complete lambda_handler. Error as follows:')
            logger.error(e)
            pass
    return response

def generate_conversation(bedrock_client,
                          model_id,
                          system_prompts,
                          messages):
    """
    Sends messages to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_prompts (JSON) : The system prompts for the model to use.
        messages (JSON) : The messages to send to the model.

    Returns:
        response (JSON): The conversation that the model generated.

    """
    cost = 0
    logger.info('INFO: beginning generate_conversation...')
    logger.info("Generating message with model %s", model_id)

    # Inference parameters to use.
    temperature = 0.5
    top_k = 200

    # Base inference parameters to use.
    inference_config = {"temperature": temperature}
    # Additional inference parameters to use.
    additional_model_fields = {"top_k": top_k}

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields
    )

    # Log token usage.
    token_usage = response['usage']
    logger.info("Input tokens: %s", token_usage['inputTokens'])
    logger.info("Output tokens: %s", token_usage['outputTokens'])
    logger.info("Total tokens: %s", token_usage['totalTokens'])
    logger.info("Stop reason: %s", response['stopReason'])
    cost += token_usage['inputTokens'] * input_cost
    cost += token_usage['outputTokens'] * output_cost
    logger.info('INFO: generate_conversation: The cost of generate_conversation is ' + str(cost))

    return response, cost

def rephrase_response(myconversation, question, answer):
    cost = 0
    logger.info('INFO: beginning rephrase_response...')
    system_prompts = [{"text": "You are an app that rephrases answers related to questions asked about National Basketball Association (NBA) statistical and salary data."}]
            
    prompt = r"""Given the following conversation history, question and answer rewrite the answer to put it in context of the original question
    and any relevant conversation history. Do not provide additional context or information that was not asked for.
    Do not explain how or why the response is better, just give the concise answer.
    Provide the concise response within <response></response> tags."""

    prompt_template = f"""{prompt}

    <conversation>
    {myconversation}
    </conversation>
    
    <question>
    {question}
    </question>

    <answer>
    {answer}
    </answer>

    """
    logger.info('INFO: rephrase_response: This is the conversation payload I am sending to the LLM:\n' + str(prompt_template))
    conversation = [
                {
                    "role": "user",
                    "content": [{"text": prompt_template}],
                }
            ]

    response, cost = generate_conversation(
        brt, model_id, system_prompts, conversation)
    logger.info('INFO: rephrase_response: This is the raw response from Bedrock:\n' + str(response))
    # Extract and print the response text.
    response_text = response["output"]["message"]["content"][0]["text"]
    
    logger.info('INFO: rephrase_response: The cost of rephrase_response is ' + str(cost))
    
    return response_text, cost
 

def lambda_handler(event, context):
    logger.info('INFO: beginning lambda_handler...')
    cost = 0
    my_response = {}
    # Check the event
    logger.info('INFO: lambda_handler: This is the event I received: %s' % (event))
    if not 'conversation' in event:
        conversation = []
    else:
        conversation = parse_conversation(event['conversation'])
    origconversation = str(conversation)
    logger.info('INFO: lambda_handler: Right after I have parsed the event the value of origconversation is:\n' + str(origconversation))
    logger.info('INFO: lambda_handler: The formatted conversation provided is:\n' + str(conversation))
    question = event['question']
    logger.info('INFO: lambda_handler: The question asked is:\n' + question)

    try:
        system_prompts = [{"text": "You are a conversational app that generates SQL code to be used with Pandas dataframes and the duckdb Python library."}]
        prompt = r"""Given the following example of two different CSV formatted files, please generate the SQL query to answer the question using any conversation provided as context.
        The table names are 'stats' and 'contracts'. For the 'stats' table, if a player played for more than one team, they will have multiple rows of 
        stats values including the 'TOT' team. The "TOT' team is for the total results for a player that played for multiple teams.
        For any column names that include '%' the values shown are decimal representations of percentages.
        If the question, conversation or answer references a specific player or players, your final response should include the player's name.
        If the SQL code requires a JOIN, tables should be joined only on 'Player-additional'. Do not use JOIN unnecessarily.
        The SQL code should be very precise and able to run with duckdb. Any column names that include a hyphen should be surrounded by double quotation marks.
        Return an XML document with the SQL between <sql></sql> in your response. 
        For example, if a user asks 'what is the average salary for a guard that scores over 20 points per game?' your response should be 
        '<sql>SELECT AVG(c."2024-25") AS Average_Salary FROM contracts c JOIN stats s ON c."Player-additional" = s."Player-additional" WHERE s.Pos = 'SG' AND COALESCE(s.PTS, (SELECT st.PTS FROM stats st WHERE "st.Player-additional" = s."Player-additional" AND st.Tm = 'TOT')) > 20;<\sql>'
        """
        prompt_template = f"""{prompt}

        <question>
        {question}
        </question>

        <csv>
        Player,Pos,Age,Tm,G,GS,MP,FG,FGA,FG%,3P,3PA,3P%,2P,2PA,2P%,eFG%,FT,FTA,FT%,ORB,DRB,TRB,AST,STL,BLK,TOV,PF,PTS,Player-additional
        Precious Achiuwa,PF-C,24,TOT,74,18,21.9,3.2,6.3,.501,0.4,1.3,.268,2.8,5.0,.562,.529,0.9,1.5,.616,2.6,4.0,6.6,1.3,0.6,0.9,1.1,1.9,7.6,achiupr01
        Precious Achiuwa,C,24,TOR,25,0,17.5,3.1,6.8,.459,0.5,1.9,.277,2.6,4.9,.528,.497,1.0,1.7,.571,2.0,3.4,5.4,1.8,0.6,0.5,1.2,1.6,7.7,achiupr01
        Precious Achiuwa,PF,24,NYK,49,18,24.2,3.2,6.1,.525,0.3,1.0,.260,2.9,5.1,.578,.547,0.9,1.4,.643,2.9,4.3,7.2,1.1,0.6,1.1,1.1,2.1,7.6,achiupr01
        Bam Adebayo,C,26,MIA,71,71,34.0,7.5,14.3,.521,0.2,0.6,.357,7.3,13.7,.528,.529,4.1,5.5,.755,2.2,8.1,10.4,3.9,1.1,0.9,2.3,2.2,19.3,adebaba01
        Ochai Agbaji,SG,23,TOT,78,28,21.0,2.3,5.6,.411,0.8,2.7,.294,1.5,2.8,.523,.483,0.5,0.7,.661,0.9,1.8,2.8,1.1,0.6,0.6,0.8,1.5,5.8,agbajoc01
        Ochai Agbaji,SG,23,UTA,51,10,19.7,2.1,4.9,.426,0.9,2.8,.331,1.2,2.1,.551,.520,0.3,0.4,.750,0.7,1.8,2.5,0.9,0.5,0.6,0.7,1.3,5.4,agbajoc01
        Ochai Agbaji,SG,23,TOR,27,18,23.6,2.7,6.8,.391,0.6,2.6,.217,2.1,4.3,.496,.432,0.8,1.3,.611,1.4,1.9,3.3,1.3,0.7,0.6,1.1,1.9,6.7,agbajoc01
        Santi Aldama,PF,23,MEM,61,35,26.5,4.0,9.3,.435,1.7,5.0,.349,2.3,4.3,.534,.528,0.9,1.4,.621,1.2,4.6,5.8,2.3,0.7,0.9,1.1,1.5,10.7,aldamsa01
        Nickeil Alexander-Walker,SG,25,MIN,82,20,23.4,2.9,6.6,.439,1.6,4.1,.391,1.3,2.5,.517,.560,0.6,0.8,.800,0.4,1.6,2.0,2.5,0.8,0.5,0.9,1.7,8.0,alexani01
        Grayson Allen,SG,28,PHO,75,74,33.5,4.5,9.1,.499,2.7,5.9,.461,1.8,3.2,.570,.649,1.7,2.0,.878,0.6,3.3,3.9,3.0,0.9,0.6,1.3,2.1,13.5,allengr01
        Jarrett Allen,C,25,CLE,77,77,31.7,6.7,10.6,.634,0.0,0.1,.000,6.7,10.6,.638,.634,3.0,4.1,.742,3.2,7.4,10.5,2.7,0.7,1.1,1.6,1.9,16.5,allenja01
        Timmy Allen,SF,24,MEM,5,0,25.0,1.2,4.6,.261,0.0,1.4,.000,1.2,3.2,.375,.261,0.2,0.4,.500,0.8,2.6,3.4,1.0,0.8,0.0,0.4,3.6,2.6,allenti01
        Jose Alvarado,PG,25,NOP,56,0,18.4,2.5,6.2,.412,1.4,3.7,.377,1.1,2.5,.464,.525,0.6,0.9,.673,0.4,1.8,2.3,2.1,1.1,0.3,0.7,1.6,7.1,alvarjo01
        Kyle Anderson,PF,30,MIN,79,10,22.6,2.5,5.5,.460,0.1,0.6,.229,2.4,4.9,.488,.472,1.2,1.7,.708,0.8,2.7,3.5,4.2,0.9,0.6,1.2,1.6,6.4,anderky01
        Bradley Beal,SG,30,PHO,53,53,33.3,7.1,13.9,.513,1.9,4.4,.430,5.2,9.4,.552,.582,2.1,2.5,.813,1.0,3.4,4.4,5.0,1.0,0.5,2.5,2.4,18.2,bealbr01
        Stephen Curry,PG,35,GSW,74,74,32.7,8.8,19.5,.450,4.8,11.8,.408,4.0,7.7,.515,.573,4.0,4.4,.923,0.5,4.0,4.5,5.1,0.7,0.4,2.8,1.6,26.4,curryst01
        Kevin Durant,PF,35,PHO,75,75,37.2,10.0,19.1,.523,2.2,5.4,.413,7.8,13.7,.567,.581,4.8,5.6,.856,0.5,6.1,6.6,5.0,0.9,1.2,3.3,1.8,27.1,duranke01
        Joel Embiid,C,29,PHI,39,39,33.6,11.5,21.8,.529,1.4,3.6,.388,10.2,18.3,.556,.561,10.2,11.6,.883,2.4,8.6,11.0,5.6,1.2,1.7,3.8,2.9,34.7,embiijo01
        Nikola Jokić,C,28,DEN,79,79,34.6,10.4,17.9,.583,1.1,2.9,.359,9.4,14.9,.626,.612,4.5,5.5,.817,2.8,9.5,12.4,9.0,1.4,0.9,3.0,2.5,26.4,jokicni01
        </csv>
     
        <csv>
        Rk,Player,Tm,2024-25,2025-26,2026-27,2027-28,2028-29,2029-30,Guaranteed,Player-additional
        1,Stephen Curry,GSW,$55761216,$59606817,,,,,$115368033,curryst01
        2,Nikola Jokić,DEN,$51415938,$55224526,$59033114,$62841702,,,$165673578,jokicni01
        3,Joel Embiid,PHI,$51415938,$55224526,$59033114,,,,$106640464,embiijo01
        4,Kevin Durant,PHO,$51179021,$54708609,,,,,$105887630,duranke01
        5,Bradley Beal,PHO,$50203930,$53666270,$57128610,,,,$103870200,bealbr01
        </csv>
        
        """
        
        conversation.append(
            {
                "role": "user",
                "content": [{"text": prompt_template}],
            }
        )
        
        logger.info('INFO: lambda_handler: The conversation being served to the LLM is: \n' + str(conversation))

        response, gen_cost = generate_conversation(
            brt, model_id, system_prompts, conversation)

        # Extract and print the response text.
        response_text = response["output"]["message"]["content"][0]["text"]
        logger.info('INFO: lambda_handler: This is the response I received from the LLM: \n' + response_text)
        cost += gen_cost
        logger.info('INFO: lambda_handler: The accumulated cost after generate_conversation is ' + str(cost))

        soup = BeautifulSoup(response_text.strip(), 'xml')
        sql_query = soup.find("sql").text.replace("\n", " ")
        logger.info('INFO: lambda_handler: This is the SQL query: \n' + str(sql_query))
        my_response['sql'] = sql_query

        statsfile = s3.get_object(Bucket='your-bucket-name', Key='NBA_2024_per_game.csv')
        #stats = pd.read_csv(io.StringIO(statsfile['Body'].read().decode('utf-8')))
        stats = pd.read_csv(statsfile['Body'])
        contractsfile = s3.get_object(Bucket='your-bucket-name', Key='2024_2025_NBA_Player_Contracts.csv')
        #contracts = pd.read_csv(io.StringIO(contractsfile['Body'].read().decode('utf-8')))
        contracts = pd.read_csv(contractsfile['Body'])
        logger.info('INFO: lambda_handler: The first 3 rows of stats are: \n' + str(stats.head(3)))
        logger.info('INFO: lambda_handler: The first 3 rows of contracts are: \n' + str(contracts.head(3)))
        logger.info('INFO: lambda_handler: Running SQL query using duckdb library.')
        #result = duckdb.query(sql_query).df()
        result = duckdb.sql(sql_query).df()
        if len(result) == 1:
            result = result.values.flatten()[0]
        logger.info('INFO: lambda_handler: This is the raw result from the SQL query: \n' + str(result))
        logger.info('INFO: lambda_handler: Right before I call rephrase_response the value of origconversation is:\n' + str(origconversation))
        answer, rephrase_cost = rephrase_response(origconversation, question, result)
        cost += rephrase_cost
        logger.info('INFO: lambda_handler: The accumulated cost after rephrase_response is ' + str(cost))
        logger.info('INFO: lambda_handler: This is the raw answer from rephrase_response:\n' + str(answer))
        newsoup = BeautifulSoup(answer.strip(), 'xml')
        final_answer = newsoup.find("response").text.replace("\n", " ")
        logger.info('INFO: lambda_handler: This is the final answer: \n' + str(final_answer))
        my_response['answer'] = final_answer
        logger.info('INFO: lambda_handler: This is the response I will return at the end of this Lambda:\n' + str(my_response))
        cost += .001
        my_response['cost'] = str(round(cost, 2))
        logger.info('INFO: lambda_handler: The accumulated cost just before I return is ' + str(cost))
        return {
            'statusCode': '200',
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': [
                my_response
            ]
        }
    except Exception as e:
        logger.error('ERROR: Unable to complete lambda_handler. Error as follows:')
        logger.error(e)
