import unittest

from flask import json

from openapi_server.models.create_node200_response import CreateNode200Response  # noqa: E501
from openapi_server.models.create_node_request import CreateNodeRequest  # noqa: E501
from openapi_server.models.delete_node200_response import DeleteNode200Response  # noqa: E501
from openapi_server.models.exec_node_method200_response import ExecNodeMethod200Response  # noqa: E501
from openapi_server.models.exec_node_method_request import ExecNodeMethodRequest  # noqa: E501
from openapi_server.models.exec_python_script200_response import ExecPythonScript200Response  # noqa: E501
from openapi_server.models.exec_python_script_request import ExecPythonScriptRequest  # noqa: E501
from openapi_server.models.get_module_help200_response import GetModuleHelp200Response  # noqa: E501
from openapi_server.models.get_node_detail200_response import GetNodeDetail200Response  # noqa: E501
from openapi_server.models.get_node_errors200_response import GetNodeErrors200Response  # noqa: E501
from openapi_server.models.get_nodes200_response import GetNodes200Response  # noqa: E501
from openapi_server.models.get_td_info200_response import GetTdInfo200Response  # noqa: E501
from openapi_server.models.get_td_python_class_details200_response import GetTdPythonClassDetails200Response  # noqa: E501
from openapi_server.models.get_td_python_classes200_response import GetTdPythonClasses200Response  # noqa: E501
from openapi_server.models.update_node200_response import UpdateNode200Response  # noqa: E501
from openapi_server.models.update_node_request import UpdateNodeRequest  # noqa: E501
from openapi_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_create_node(self):
        """Test case for create_node

        Create a new node
        """
        create_node_request = openapi_server.CreateNodeRequest()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/nodes',
            method='POST',
            headers=headers,
            data=json.dumps(create_node_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_delete_node(self):
        """Test case for delete_node

        Delete an existing node
        """
        query_string = [('nodePath', 'node_path_example')]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/nodes',
            method='DELETE',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_exec_node_method(self):
        """Test case for exec_node_method

        Call a method of the specified node
        """
        exec_node_method_request = openapi_server.ExecNodeMethodRequest()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/td/nodes/exec',
            method='POST',
            headers=headers,
            data=json.dumps(exec_node_method_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_exec_python_script(self):
        """Test case for exec_python_script

        Execute python code on the server
        """
        exec_python_script_request = openapi_server.ExecPythonScriptRequest()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/td/server/exec',
            method='POST',
            headers=headers,
            data=json.dumps(exec_python_script_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_module_help(self):
        """Test case for get_module_help

        Get module/class Python help documentation
        """
        query_string = [('moduleName', 'module_name_example')]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/td/modules/help',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_node_detail(self):
        """Test case for get_node_detail

        Get node detail
        """
        query_string = [('nodePath', 'node_path_example')]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/nodes/detail',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_node_errors(self):
        """Test case for get_node_errors

        Get node errors
        """
        query_string = [('nodePath', 'node_path_example')]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/nodes/errors',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_nodes(self):
        """Test case for get_nodes

        Get nodes in the path
        """
        query_string = [('parentPath', 'parent_path_example'),
                        ('pattern', '*'),
                        ('includeProperties', False)]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/nodes',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_td_info(self):
        """Test case for get_td_info

        Get TouchDesigner information
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/td/server/td',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_td_python_class_details(self):
        """Test case for get_td_python_class_details

        Get details of a specific Python class or module
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/td/classes/{class_name}'.format(class_name='class_name_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_td_python_classes(self):
        """Test case for get_td_python_classes

        Get a list of Python classes and modules
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/td/classes',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_update_node(self):
        """Test case for update_node

        Update node properties
        """
        update_node_request = openapi_server.UpdateNodeRequest()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/nodes/detail',
            method='PATCH',
            headers=headers,
            data=json.dumps(update_node_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
