import connexion
from typing import Dict
from typing import Tuple
from typing import Union

from openapi_server.models.managed_cluster import ManagedCluster  # noqa: E501
from openapi_server.models.metadata import Metadata  # noqa: E501
from openapi_server.models.spec import Spec  # noqa: E501
from openapi_server import util

managed_cluster = {
    "test1": ManagedCluster(
        "cluster.open-cluster-management.io/v1",
        "ManagedCluster",
        Metadata("test1"),
        Spec(True, None),
        "test1 cluster in service",
    ),
}


def cluster_open_cluster_management_io_v1_managedclusters_cluster_name_delete():  # noqa: E501
    """Delete a single cluster

     # noqa: E501


    :rtype: Union[ManagedCluster, Tuple[ManagedCluster, int], Tuple[ManagedCluster, int, Dict[str, str]]
    """
    return "do some magic!"


def create_cluster(
    api_version=None, kind=None, metadata=None, spec=None, status=None
):  # noqa: E501
    """Create a cluster

     # noqa: E501

    :param api_version:
    :type api_version: str
    :param kind:
    :type kind: str
    :param metadata:
    :type metadata: dict | bytes
    :param spec:
    :type spec: dict | bytes
    :param status:
    :type status: str

    :rtype: Union[ManagedCluster, Tuple[ManagedCluster, int], Tuple[ManagedCluster, int, Dict[str, str]]
    """
    if connexion.request.is_json:
        request_json = connexion.request.get_json()
        if "metadata" in request_json:
            metadata = Metadata.from_dict(request_json["metadata"])  # noqa: E501
        if "spec" in request_json:
            spec = Spec.from_dict(request_json["spec"])  # noqa: E501
    cluster = ManagedCluster(api_version, kind, metadata, spec, status)
    managed_cluster[metadata.name] = cluster
    return "cluster created", 200


def get_cluster(cluster_name):  # noqa: E501
    """Query a single cluster for more details

     # noqa: E501

    :param cluster_name: The name of the cluster to retrieve
    :type cluster_name: str

    :rtype: Union[ManagedCluster, Tuple[ManagedCluster, int], Tuple[ManagedCluster, int, Dict[str, str]]
    """
    if cluster_name in managed_cluster:
        return managed_cluster[cluster_name]
    else:
        return "Cluster not found", 404


def list_managed_clusters():  # noqa: E501
    """Query your clusters for more details.

     # noqa: E501


    :rtype: Union[List[ManagedCluster], Tuple[List[ManagedCluster], int], Tuple[List[ManagedCluster], int, Dict[str, str]]
    """
    return list(managed_cluster.values())
