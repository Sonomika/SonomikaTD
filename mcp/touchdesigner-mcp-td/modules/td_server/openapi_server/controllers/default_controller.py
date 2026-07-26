import connexion
from typing import Dict
from typing import Tuple
from typing import Union

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
from openapi_server import util


def create_node(body):  # noqa: E501
    """Create a new node

     # noqa: E501

    :param create_node_request: 
    :type create_node_request: dict | bytes

    :rtype: Union[CreateNode200Response, Tuple[CreateNode200Response, int], Tuple[CreateNode200Response, int, Dict[str, str]]
    """
    create_node_request = body
    if connexion.request.is_json:
        create_node_request = CreateNodeRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def delete_node(node_path):  # noqa: E501
    """Delete an existing node

     # noqa: E501

    :param node_path: Path to the node to delete. e.g., \&quot;/project1/geo1\&quot;
    :type node_path: str

    :rtype: Union[DeleteNode200Response, Tuple[DeleteNode200Response, int], Tuple[DeleteNode200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def exec_node_method(body):  # noqa: E501
    """Call a method of the specified node

    Call a method on the node at the specified path (e.g., /project1). This allows operations equivalent to TouchDesigner&#39;s Python API such as &#x60;parent_comp &#x3D; op(&#39;/project1&#39;)&#x60; and &#x60;parent_comp.create(&#39;textTOP&#39;, &#39;myText&#39;)&#x60;.  # noqa: E501

    :param exec_node_method_request: 
    :type exec_node_method_request: dict | bytes

    :rtype: Union[ExecNodeMethod200Response, Tuple[ExecNodeMethod200Response, int], Tuple[ExecNodeMethod200Response, int, Dict[str, str]]
    """
    exec_node_method_request = body
    if connexion.request.is_json:
        exec_node_method_request = ExecNodeMethodRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def exec_python_script(body):  # noqa: E501
    """Execute python code on the server

    Execute a Python script directly in TouchDesigner. Multiline scripts and scripts containing comments are supported. The script can optionally set a &#x60;result&#x60; variable to explicitly return a value. This endpoint allows you to interact with TouchDesigner nodes programmatically.  # noqa: E501

    :param exec_python_script_request: 
    :type exec_python_script_request: dict | bytes

    :rtype: Union[ExecPythonScript200Response, Tuple[ExecPythonScript200Response, int], Tuple[ExecPythonScript200Response, int, Dict[str, str]]
    """
    exec_python_script_request = body
    if connexion.request.is_json:
        exec_python_script_request = ExecPythonScriptRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def get_module_help(module_name):  # noqa: E501
    """Get module/class Python help documentation

    Retrieve Python help() documentation for TouchDesigner modules, classes, or utilities like tdu. # noqa: E501

    :param module_name: Module or class name (e.g., \&quot;noiseCHOP\&quot;, \&quot;td.noiseCHOP\&quot;, \&quot;tdu\&quot;).
    :type module_name: str

    :rtype: Union[GetModuleHelp200Response, Tuple[GetModuleHelp200Response, int], Tuple[GetModuleHelp200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def get_node_detail(node_path):  # noqa: E501
    """Get node detail

    Retrieves detailed information about a specific node including its properties, parameters and connections # noqa: E501

    :param node_path: Node path. e.g., \&quot;/project1/textTOP\&quot;
    :type node_path: str

    :rtype: Union[GetNodeDetail200Response, Tuple[GetNodeDetail200Response, int], Tuple[GetNodeDetail200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def get_node_errors(node_path):  # noqa: E501
    """Get node errors

    Collects TouchDesigner error messages for a node and its children # noqa: E501

    :param node_path: Absolute path to the node to inspect. e.g., \&quot;/project1/text1\&quot;
    :type node_path: str

    :rtype: Union[GetNodeErrors200Response, Tuple[GetNodeErrors200Response, int], Tuple[GetNodeErrors200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def get_nodes(parent_path, pattern=None, include_properties=None):  # noqa: E501
    """Get nodes in the path

     # noqa: E501

    :param parent_path: Parent path  e.g., \&quot;/project1\&quot;
    :type parent_path: str
    :param pattern: Pattern to match against node names e.g., \&quot;null*\&quot;
    :type pattern: str
    :param include_properties: Whether to include full node properties in the response (default false for better performance)
    :type include_properties: bool

    :rtype: Union[GetNodes200Response, Tuple[GetNodes200Response, int], Tuple[GetNodes200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def get_td_info():  # noqa: E501
    """Get TouchDesigner information

    Returns information about the TouchDesigner # noqa: E501


    :rtype: Union[GetTdInfo200Response, Tuple[GetTdInfo200Response, int], Tuple[GetTdInfo200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def get_td_python_class_details(class_name):  # noqa: E501
    """Get details of a specific Python class or module

    Returns detailed information about a specific Python class, module, or function including methods, properties, and documentation # noqa: E501

    :param class_name: Name of the class or module. e.g., \&quot;textTOP\&quot;
    :type class_name: str

    :rtype: Union[GetTdPythonClassDetails200Response, Tuple[GetTdPythonClassDetails200Response, int], Tuple[GetTdPythonClassDetails200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def get_td_python_classes():  # noqa: E501
    """Get a list of Python classes and modules

    Returns a list of Python classes, modules, and functions available in TouchDesigner # noqa: E501


    :rtype: Union[GetTdPythonClasses200Response, Tuple[GetTdPythonClasses200Response, int], Tuple[GetTdPythonClasses200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def update_node(body=None):  # noqa: E501
    """Update node properties

     # noqa: E501

    :param update_node_request: 
    :type update_node_request: dict | bytes

    :rtype: Union[UpdateNode200Response, Tuple[UpdateNode200Response, int], Tuple[UpdateNode200Response, int, Dict[str, str]]
    """
    update_node_request = body
    if connexion.request.is_json:
        update_node_request = UpdateNodeRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
