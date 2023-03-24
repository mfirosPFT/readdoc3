

Cloudformation Template
=======================
.. contents:: Table of Contents
   :local:
   :depth: 3
   :backlinks: none

.. toctree::
   :maxdepth: 4

SAM Template Anatomy
--------------------
This section describes the anatomy of the SAM template. The SAM template is a YAML file that defines the resources that are created by the template. The resources are defined by their type and properties. The properties are specific to the resource type. For example, the AWS::Serverless::Function resource type has properties that define the function code, runtime, handler, and other function properties.

The following example shows a YAML-formatted template fragment:

    .. code-block:: yaml

        Transform: AWS::Serverless-2016-10-31

        Globals:
            set of globals

        Description:
            String

        Metadata:
            template metadata

        Parameters:
            set of parameters

        Mappings:
            set of mappings

        Conditions:
            set of conditions

        Resources:
            set of resources

        Outputs:
            set of outputs

Architecture
------------
The following diagram shows the architecture of the solution.

.. image:: ../template.png
   :alt: Architecture

A more understandable diagram is shown below.

.. image:: ../aws.png
   :alt: Architecture
   
Globals
-------
This section defines the global properties that are applied to all resources in the template. For example Tags, Tracing, etc.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 3-14
   :caption: template.yaml - Globals

Conditions
----------
This section defines the conditions that are used to control the creation of resources in the template. The conditions are used to control the creation of resources based on the value of a parameter. For example, the following condition creates the Step function only if the DeployStepFunction parameter is set to true.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 15-19
   :caption: template.yaml - Conditions
   
Parameters
-----------
This section defines the parameters that can be passed to the template. The parameters are used to configure the resources in the template.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 20-44
   :caption: template.yaml - Parameters

Resources
---------
This section defines the resources that are created by the template. The resources are defined by their type and properties. The properties are specific to the resource type. For example, the AWS::Serverless::Function resource type has properties that define the function code, runtime, handler, and other function properties.

API Gateway
~~~~~~~~~~~

API Gateway Secret Key
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the API Gateway Secret Key. The API Gateway Secret Key is used to secure the API Gateway endpoint. The API Gateway Secret Key is passed to the API Gateway as a header value. The API Gateway Secret Key is used to validate the request before the request is forwarded to the Lambda function.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 46-68
   :caption: template.yaml - API Gateway Secret Key

Main API Gateway Endpoint
^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the API Gateway. The API Gateway is used to expose the Lambda function as a REST API endpoint. The API Gateway is configured to use the API Gateway Secret Key to secure the API Gateway endpoint.

Methods:
               - /run 
               - /query


.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 118-217
   :caption: template.yaml - API Gateway

SSMActivationApi
^^^^^^^^^^^^^^^^^^^^
This section defines the API Gateway. The API Gateway is used to expose the Lambda function as a REST API endpoint. The API Gateway is configured to use the API Gateway Secret Key to secure the API Gateway endpoint.

Methods:
               - /ssmactivation
               - /addtags

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 402-431
   :caption: template.yaml - SSMActivationApi

SSMInstallScriptGeneratorApi
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the API Gateway. The API Gateway is used to expose the Lambda function as a REST API endpoint. 

Methods:
               - /ssminstallscriptgenerator

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 456-475
   :caption: template.yaml - SSMInstallScriptGeneratorApi

StateMachineApi
^^^^^^^^^^^^^^^^
This section defines the API Gateway. The API Gateway is used to expose the Lambda function as a REST API endpoint. This is optional, depends on deployment of step function.

Methods:
               - /run
               - /query

.. literalinclude:: ../template.yml
    :language: yaml
    :linenos:
    :lines: 1363-1442
    :caption: template.yaml - StateMachineApi

Lambda Functions
~~~~~~~~~~~~~~~~~~
This section defines the Lambda function. The Lambda function is used to run the SSM Run document and query the SSM Run document status. Act as Custom Authorizer for API Gateway. Dashboard Function to get the status of the SSM Run document. SSM Agent Activation Function to activate the SSM Agent on the managed instance. SSM Install Script Generator Function to generate the SSM Install Script.

Custom Authorizer
^^^^^^^^^^^^^^^^^^^^^
This section defines the Custom Authorizer. The Custom Authorizer is used to validate the API Gateway Secret Key. The Custom Authorizer is configured to use the API Gateway Secret Key to validate the request.

.. note::

   *CodeUri* below is set to a location of CustomAuthorizer, see :doc:`CustomAuthorizer` for more information.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 69-81
   :caption: template.yaml - Custom Authorizer

ExpeDatSSMRunDocumet
^^^^^^^^^^^^^^^^^^^^^
This section defines the Lambda function that runs the SSM Run document. The Lambda function is configured to use the API Gateway Secret Key to validate the request.

.. note::
    *CodeUri* below is set to a location of ExpeDatSSMRunDocumet, see :doc:`ExpeDatSSMRunDocumet` for more information.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 218-246
   :caption: template.yaml - ExpeDatSSMRunDocumet

ExpeDatSSMInvocationQuery
^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the Lambda function that queries the SSM Run document status. The Lambda function is configured to use the API Gateway Secret Key to validate the request.

.. note::
    *CodeUri* below is set to a location of ExpeDatSSMInvocationQuery, see :doc:`ExpeDatSSMInvocationQuery` for more information.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 247-271
   :caption: template.yaml - ExpeDatSSMInvocationQuery

SSMAgentActivation
^^^^^^^^^^^^^^^^^^^^
This section defines the Lambda function that activates the SSM Agent on the managed instance. The Lambda function is configured to use the API Gateway Secret Key to validate the request.

.. note::
    *CodeUri* below is set to a location of SSMAgentActivation, see :doc:`SSMAgentActivation` for more information.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 272-304
   :caption: template.yaml - SSMAgentActivation

SSMNotification
^^^^^^^^^^^^^^^^
This section defines the Lambda function that sends the SSM Run document status notification using SES. The Lambda function is configured to use the API Gateway Secret Key to validate the request.

.. note::
    *CodeUri* below is set to a location of SSMNotification, see :doc:`SSMNotification` for more information.


.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 305-330
   :caption: template.yaml - SSMNotification

SSMInstallScriptGenerator
^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the Lambda function that generates the SSM Install Script. This is a public API without any authentication.

.. note::
    *CodeUri* below is set to a location of SSMInstallScriptGenerator, see :doc:`SSMInstallScriptGenerator` for more information.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 432-455
   :caption: template.yaml - SSMInstallScriptGenerator

DashboardFunction
^^^^^^^^^^^^^^^^^^^
This section defines the Lambda function that gets the status of the SSM Run document, cost and usage to be used by Cloudwatch Dashboard. 

.. note::
    *CodeUri* below is set to a location of DashboardFunction, see :doc:`DashboardFunction` for more information.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1054-1065
   :caption: template.yaml - DashboardFunction

SNS Topic
~~~~~~~~~~

SNSNotificationTopic
^^^^^^^^^^^^^^^^^^^^^^
This section defines the SNS Topic. The SNS Topic is used to send the SSM Run document status notification.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 809-825
   :caption: template.yaml - SNSNotificationTopic

SSM Document
~~~~~~~~~~~~~~~~

SSMDocument
^^^^^^^^^^^^^^
This section defines the SSM Document. The SSM Document is used to run the SSM Run document.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 856-914
   :caption: template.yaml - SSMDocument

SSM Parameters Store
~~~~~~~~~~~~~~~~~~~~~~

ExpeDatUserParameterName
^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the SSM Parameter Store. The SSM Parameter Store is used to store the SSM Run document user parameter name.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 915-928
   :caption: template.yaml - ExpeDatUserParameterName

ExpeDatPassParameterName
^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the SSM Parameter Store. The SSM Parameter Store is used to store the SSM Run document password parameter name.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 929-942
   :caption: template.yaml - ExpeDatPassParameterName

ExpeDatServerParameterName
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the SSM Parameter Store. The SSM Parameter Store is used to store the SSM Run document server parameter name.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 943-956
   :caption: template.yaml - ExpeDatServerParameterName

SSMActivationParameter
^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the SSM Parameter Store. The SSM Parameter Store is used to store the SSM Activation Code and ID.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 957-970
   :caption: template.yaml - SSMActivationParameter

DynamoDB Table
~~~~~~~~~~~~~~~~

DynamoDBTableTheater
^^^^^^^^^^^^^^^^^^^^^^
This section defines the DynamoDB Table. The DynamoDB Table is used to store the theater box metadata.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 987-1017
   :caption: template.yaml - DynamoDBTableTheater
   
DynamoDBTableStatus
^^^^^^^^^^^^^^^^^^^^^
This section defines the DynamoDB Table. The DynamoDB Table is used to store the SSM Run document status.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1018-1053
   :caption: template.yaml - DynamoDBTableStatus

Cloudwatch Dashboard
~~~~~~~~~~~~~~~~~~~~~~

CloudwatchDashboard
^^^^^^^^^^^^^^^^^^^^^
This section defines the Cloudwatch Dashboard. The Cloudwatch Dashboard is used to display the SSM Run document status, cost and usage. API Gateway, Lambda, DynamoDB and SNS metrics are also displayed.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1114-1288
   :caption: template.yaml - CloudwatchDashboard

Step Functions
~~~~~~~~~~~~~~~~

StateMachineExpressSync
^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the Step Functions. The Step Functions is used to run the SSM Run document. This is optional and can be set using Parameters section.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1289-1354
   :caption: template.yaml - StateMachineExpressSync

IAM Role
~~~~~~~~~~
CustomAuthorizerRole
^^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the API Gateway to invoke the Lambda function.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 82-117
   :caption: template.yaml - CustomAuthorizerRole

SSMNotificationRole
^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to send the SSM Run document status notification using SES.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 331-401
   :caption: template.yaml - SSMNotificationRole

SSMInstallScriptGeneratorRole
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to generate the SSM Install Script.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 476-507
   :caption: template.yaml - SSMInstallScriptGeneratorRole

ExpeDatSSMRunDocumetRole
^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to run the SSM Run document.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 520-601
   :caption: template.yaml - ExpeDatSSMRunDocumetRole

ExpeDatSSMInvocationQueryRole
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to query the SSM Run document status.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 601-675
   :caption: template.yaml - ExpeDatSSMInvocationQueryRole

SSMAgentActivationRole
^^^^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to activate the SSM Agent.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 676-735
   :caption: template.yaml - SSMAgentActivationRole

SSMAgentRole
^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to run the SSM Run document on managed instance.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 736-808
   :caption: template.yaml - SSMAgentRole

SSMSNSPublishRole
^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to publish the SSM Run document status to SNS.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 826-855
   :caption: template.yaml - SSMSNSPublishRole

DashboardFunctionRole
^^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Lambda function to query the SSM run commands, Cost and usage.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1066-1113
   :caption: template.yaml - DashboardFunctionRole

StateMachineApiRole
^^^^^^^^^^^^^^^^^^^^^
This section defines the IAM Role. The IAM Role is used to allow the Step Functions to invoke the Lambda function.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1443-1465
   :caption: template.yaml - StateMachineApiRole

Outputs
---------
This section defines the Outputs. The Outputs is used to display the API Gateway URL, Dashboard URL and Installation script URL.

.. literalinclude:: ../template.yml
   :language: yaml
   :linenos:
   :lines: 1466-1482
   :caption: template.yaml - Outputs
