
//cognito-auth.js
var AWS;
var APP = window.APP || {};
var credKeys = [
    'accessKeyId',
    'secretAccessKey',
    'sessionToken'
];
AWS.config.logger = console;
window.sessionStorage;
window.userPool;

(function scopeWrapper($) {

    AWS.config.region = _config.cognito.region;
   
    var poolData = {
        UserPoolId: _config.cognito.userPoolId,
        ClientId: _config.cognito.userPoolClientId
    };
   
    if (!(_config.cognito.userPoolId &&
        _config.cognito.userPoolClientId &&
        _config.cognito.region)) {
      $('#noCognitoMessage').show();
      return;
    }

    userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

    if (typeof AWSCognito !== 'undefined') {
        AWSCognito.config.region = _config.cognito.region;
    }

    function signin(username, password, signinSuccess, signinFailure) {
        var authenticationData = {
            Username: username,
            Password: password,
        };
       
        var authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails(
            authenticationData
        );

        var userData = {
            Username: username,
            Pool: userPool,
        };

        var cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);
        cognitoUser.authenticateUser(authenticationDetails, {
            onSuccess: function(result) {
                var accessToken = result.getAccessToken().getJwtToken();
                console.log('My cognitoUser accessToken from cognito-auth.js is: ' + accessToken);

                console.log('I THINK am updating my AWS config with credentials in cognito-auth.js.');
                AWS.config.credentials = new AWS.CognitoIdentityCredentials({
                    //credentials: new AWS.CognitoIdentityCredentials({
                        IdentityPoolId: 'us-east-1:xxxxxx-xxxx-xxxx-xxxx-xxxxxx', // your identity pool id here
                        Logins: {
                            // Change the key below according to the specific region your user pool is in.
                            'cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxxx': result
                                .getIdToken()
                                .getJwtToken(),
                        },
                    //})
                });

                console.log('This is the contents of my AWS config in cognito-auth.js before credentials.get: ')
                const keys = Object.keys(AWS.config.credentials);
                keys.forEach((key, index) => {
                    console.log(`${key}: ${AWS.config.credentials[key]}`);
                });

                //refreshes credentials using AWS.CognitoIdentity.getCredentialsForIdentity()
                AWS.config.credentials.refresh(error => {
                    console.log('I am in the config credentials refresh section in in cognito-auth.js.')
                    if (error) {
                        console.error(error);
                    } else {
                        // Instantiate aws sdk service objects now that the credentials have been updated.
                        // example: var s3 = new AWS.S3();
                        console.log('Successfully refreshed AWS credentials in in cognito-auth.js!');
                        //console.log(AWS.config.credentials.accessKey);
                        console.log(AWS.config);
                        //signinSuccess();
                        // Get the Amazon Cognito ID token for the user. 'getToken()' below.
                    }
                });

                credKeys.forEach(function(key) {
                    sessionStorage.setItem(key, AWS.config.credentials[key]);
                });

                credKeys.forEach(function(key) {
                    AWS.config.credentials[key] = sessionStorage.getItem(key);
                });
                
                signinSuccess();
                console.log('At the end of signin my credentials are no longer valid in cognito-auth.js: ' + AWS.config.credentials.expired)
            },

            onFailure: function(err) {
                //alert(err.message || JSON.stringify(err));
                console.log('The onFailure method of the signing has been called. This is the error received: '+err)
                if (err != "Error: New password is required."){
                    signinFailure();
                }
            },

            mfaRequired: function(codeDeliveryDetails) {
                // MFA is required to complete user authentication.
                // Get the code from user and call
                cognitoUser.sendMFACode(mfaCode, this)
            },

            newPasswordRequired: function(userAttributes, requiredAttributes) {
                // User was signed up by an admin and must provide new
                // password and required attributes, if any, to complete
                // authentication.
                //let newPassword = prompt('A new password is required!');
                const dialog = document.querySelector('dialog')
                const form = document.getElementById("newPasswordForm")
                const inputPassword = document.querySelector('#input-password')
                form.reset()
                //dialog.style.display = 'block';
                dialog.showModal();

                form.onsubmit = (e) => {
                    e.preventDefault();
                    let newPassword = inputPassword.value
                    //dialog.style.display = 'none';
                    dialog.close()
                
                    // the api doesn't accept this field back
                    delete userAttributes.email_verified;

                    // store userAttributes on global variable
                    sessionUserAttributes = userAttributes;

                    //handleNewPassword(newPassword);
                    cognitoUser.completeNewPasswordChallenge(newPassword, {}, this)
                }
            }
        });
    }

    /*
     *  Event Handlers
     */

    $(function onDocReady() {
        $('#signinForm').submit(handleSignin);
        //document.getElementById("newPasswordDialog").close()
        //$('#signoutForm').submit(handleSignout);
    });

    function hide (elements) {
        elements = elements.length ? elements : [elements];
        for (var index = 0; index < elements.length; index++) {
            elements[index].style.display = 'none';
        }
    }

    function show (elements, specifiedDisplay) {
        elements = elements.length ? elements : [elements];
        for (var index = 0; index < elements.length; index++) {
            elements[index].style.display = specifiedDisplay || 'block';
        }
    }

    function handleSignin(event) {
        var username = $('#usernameInputSignin').val();
        var password = $('#passwordInputSignin').val();
        event.preventDefault();
        signin(username, password,
            function signinSuccess() {
                window.location.href = 'app.html';
            },
            function signinError(err) {
                //alert(err)
                console.log('The signinError has been called. This is the error received: ' + err)
                window.location.href = 'signin.html';
            }
        );
    }

}(jQuery));