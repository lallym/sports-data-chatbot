// app.js
var AWS;
var APP = window.APP || {};
AWS.config.logger = console;
AWS.config.region = 'us-east-1';
window.sessionStorage;
var poolData = {
  UserPoolId: _config.cognito.userPoolId,
  ClientId: _config.cognito.userPoolClientId
};
let userPool = window.userPool;
let cognitoUser = userPool.getCurrentUser();
let lambda;
let conversationhist = '';

(function appScopeWrapper($) {

  signOut = function signOut() {
    console.log('Signing out.');
    cognitoUser.signOut();
    window.location.href = 'signin.html';
  };

  function sleep(ms = 0) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function escapeQuotes(str) {
    return str.replace(/"/g, '\\"').replace(/'/g, "\\'");
  }

  function checkuser(cognitoUser){
    if (cognitoUser != null) {
      console.log('In app.js:50 I have an existing cognitoUser.');
      cognitoUser.getSession(function(err, result) {
        if (result) {
          console.log('You are logged in.');

          AWS.config.region = 'us-east-1';
          // Add the User's Id Token to the Cognito credentials login map.
          AWS.config.credentials = new AWS.CognitoIdentityCredentials({
            IdentityPoolId: 'us-east-1:xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx', // your identity pool id here
            Logins: {
                // Change the key below according to the specific region your user pool is in.
                'cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxxxxx': result
                    .getIdToken()
                    .getJwtToken(),
            },
          });
          lambda = new AWS.Lambda();
          const keys = Object.keys(AWS.config.credentials);
            keys.forEach((key, index) => {
                console.log(`${key}: ${AWS.config.credentials[key]}`);
            });
        } else {
          console.log('In app.js:53 there has been an error verifying cognitoUser.')
          console.error(err);
          window.location.href = 'signin.html';
        }
      });
    } else {
      console.log('In app.js:59 there is no current cognitoUser.')
      window.location.href = 'signin.html';
    }
  };

  function callChatLambda() {
    document.getElementById("resetForm").style.display="block";
    //myquestion = document.getElementById("chat").value
    myquestion = document.getElementById("chat").innerHTML
    //document.getElementById("chat").value = ''
    document.getElementById("chat").innerHTML = ''
    document.getElementById("sql").innerHTML = ''
    document.getElementById("cost").innerHTML = ''
    document.getElementById("buttonwrapper").style.display = "none";
    let oldconversationhist = escapeQuotes(conversationhist);
    conversationhist = conversationhist + "<div class=\"user\">user: " + myquestion + "</div><br/>";
    document.getElementById("chatlog").innerHTML = '';
    document.getElementById("chatlog").innerHTML = conversationhist;
    window.moveBy(0,5);
    displayLoading();
    var params = {
      FunctionName: 'basketballChatbot', /* required */
      InvocationType: "RequestResponse",
      LogType: "None",
      Payload: '{ "conversation": "'+oldconversationhist+'", "question": "'+myquestion+'"}'
    };
    console.log(params);
    lambda.invoke(params, function(err, data) {
      if (err) {
        console.log(err, err.stack); // an error occurred
      } else {
        console.log(data);           // successful response
        myresponse = JSON.parse(data.Payload);
        if (myresponse === undefined || myresponse === null){
          conversationhist = conversationhist + "<div class=\"assistant\">assistant: I apologize, there was an error. Please try rewording your question.</div><br/>";
        } else if (myresponse.body[0].hasOwnProperty('answer')) {
          conversationhist = conversationhist + "<div class=\"assistant\">assistant: " + myresponse.body[0].answer + "</div><br/>";
          if (myresponse.body[0].hasOwnProperty('sql')) {
            mysql = "<div class=\"sql\">The generated SQL statement is:<br/>" + myresponse.body[0].sql + "</div>";
            document.getElementById("sql").innerHTML = mysql;
          }
          if (myresponse.body[0].hasOwnProperty('cost')) {
            document.getElementById("cost").innerHTML = "The estimated cost to generate this answer is: $" + myresponse.body[0].cost;
          }
        } else {
          conversationhist = conversationhist + "<div class=\"assistant\">assistant: I apologize, there was an error. Please try rewording your question.</div><br/>";
          console.log(myresponse.body)
        }
        document.getElementById("chatlog").innerHTML = conversationhist;
        /*document.getElementById("cost").innerHTML = "This processing is estimated to cost "+parseFloat(myresponse.body.cost.total).toFixed(2);*/
        hideLoading();
        document.getElementById("buttonwrapper").style.display = "block";
      }
    });
  };
    
  function resetPage() {
    document.getElementById("chatlog").innerHTML = '';
    //document.getElementById("chat").value = '';
    document.getElementById("chat").innerHTML = '';
    document.getElementById("sql").innerHTML = '';
    document.getElementById("cost").innerHTML = '';
    document.getElementById("content").style.display="none";
    document.getElementById("resetForm").style.display="none";
    conversationhist = ''
  };


  /*
  *  Event Handlers
  */

  $(function onDocReady() {
    checkuser(cognitoUser);
    $('#chatbtn').click(handleChat);
    $('#resetlForm').submit(handleReset);
    $('#signoutForm').submit(handleSignout);
    document.getElementById("chat").addEventListener("keydown", function (event) {
      if (event.key === 'Enter') {
          // Check if Enter key is pressed
          document.getElementById("chatbtn").click();
          // Trigger button click
      }
  });
  });


  const loaderContainer = document.getElementById('loadermodal');
  const displayLoading = () => {
      //loaderContainer.style.display = 'block';
      loaderContainer.showModal()
  };

  const hideLoading = () => {
      //loaderContainer.style.display = 'none';
      loaderContainer.close()
  };


  function handleChat(event) {
    event.preventDefault();
    callChatLambda(
        function Success() {
            
        },
        function Error(err) {
            alert(err);
            alert('Please remember this is a demo. There was an unspecified error. Please try again. If that does not work, please contact your AWS Team.');
            document.getElementById("chatlog").innerHTML = '';
            document.getElementById("chat").value = '';
            document.getElementById("content").style.display="none";
            document.getElementById("againForm").style.display="none";
            document.getElementById("newmodelForm").style.display="none";
        }
    );
  }

  function handleReset(event) {
    event.preventDefault();
    resetPage(
        function Success() {
            
        },
        function Error(err) {
            alert(err);
            alert('Please remember this is a demo. There was an unspecified error. Please try again. If that does not work, please contact your AWS Team: Erik, Mike and Dash, directly.');
            document.getElementById("chatlog").value = '';
            document.getElementById("chat").value = '';
            document.getElementById("content").style.display="none";
            document.getElementById("againForm").style.display="none";
            document.getElementById("resetForm").style.display="none";
        }
    );
  }

  function handleSignout(event) {
    signOut();
  }


}(jQuery));