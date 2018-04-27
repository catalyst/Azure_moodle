import sys
import time

from azure.mgmt.resource import ResourceManagementClient
from msrestazure.azure_active_directory import ServicePrincipalCredentials

from travis.Configuration import Configuration

DEPLOYMENT_NAME = 'azure-moodle-deployment-test'


class DeploymentTester:
    ERROR_VALIDATION_FAILED = 1

    def __init__(self):
        self.config = Configuration()

        self.credentials = None
        """:type : ServicePrincipalCredentials"""

        self.resource_client = None
        """:type : ResourceManagementClient"""

    def run(self):
        self.check_configuration()
        self.login()
        self.create_resource_group()
        # self.validate()
        self.deploy()
        print('Job done!')

    def check_configuration(self):
        print('Checking configuration...')
        if not self.config.is_valid():
            print('No Azure deployment info given, skipping test deployment and exiting.')
            print('Further information: https://github.com/Azure/Moodle#automated-testing-travis-ci')
            sys.exit()

    def login(self):
        print('Logging in...')
        self.credentials = ServicePrincipalCredentials(
            client_id=self.config.client_id,
            secret=self.config.secret,
            tenant=self.config.tenant_id,
        )
        self.resource_client = ResourceManagementClient(self.credentials, self.config.subscription_id)

    def create_resource_group(self):
        print('Creating group "{}" on "{}"...'.format(self.config.resource_group, self.config.location))
        self.resource_client.resource_groups.create_or_update(self.config.resource_group,
                                                              {'location': self.config.location})

    def validate(self):
        print('Validating deployment...')

        validation = self.resource_client.deployments.validate(self.config.resource_group,
                                                               self.config.deployment_name,
                                                               self.config.deployment_properties)
        if validation.error is not None:
            print("*** VALIDATION FAILED ***")
            print(validation.error.message)
            sys.exit(DeploymentTester.ERROR_VALIDATION_FAILED)

    def deploy(self):
        print('Running Azure build step...')
        deployment = self.resource_client.deployments.create_or_update(self.config.resource_group,
                                                                       self.config.deployment_name,
                                                                       self.config.deployment_properties)
        """:type : msrestazure.azure_operation.AzureOperationPoller"""
        started = time.time()
        while not deployment.done():
            print('... after {} got status {}, still waiting ...'.format(self.elapsed(started), deployment.status()))
            deployment.wait(60)
        print("The waiting is over! After {} got status: {}".format(self.elapsed(started), deployment.status()))

    def elapsed(self, since):
        elapsed = int(time.time() - since)
        elapsed = '{:02d}:{:02d}:{:02d}'.format(elapsed // 3600, (elapsed % 3600 // 60), elapsed % 60)
        return elapsed
