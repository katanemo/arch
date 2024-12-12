import unittest

from flask import json

from openapi_server.models.managed_cluster import ManagedCluster  # noqa: E501
from openapi_server.models.metadata import Metadata  # noqa: E501
from openapi_server.models.spec import Spec  # noqa: E501
from openapi_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_cluster_open_cluster_management_io_v1_managedclusters_cluster_name_delete(
        self,
    ):
        """Test case for cluster_open_cluster_management_io_v1_managedclusters_cluster_name_delete

        Delete a single cluster
        """
        headers = {
            "Accept": "application/json",
        }
        response = self.client.open(
            "/cluster.open-cluster-management.io/v1/managedclusters/{cluster_name}",
            method="DELETE",
            headers=headers,
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    @unittest.skip("multipart/form-data not supported by Connexion")
    def test_create_cluster(self):
        """Test case for create_cluster

        Create a cluster
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "multipart/form-data",
        }
        data = dict(
            api_version="api_version_example",
            kind="kind_example",
            metadata=openapi_server.Metadata(),
            spec=openapi_server.Spec(),
            status="status_example",
        )
        response = self.client.open(
            "/cluster.open-cluster-management.io/v1/managedclusters",
            method="POST",
            headers=headers,
            data=data,
            content_type="multipart/form-data",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_get_cluster(self):
        """Test case for get_cluster

        Query a single cluster for more details
        """
        headers = {
            "Accept": "application/json",
        }
        response = self.client.open(
            "/cluster.open-cluster-management.io/v1/managedclusters/{cluster_name}",
            method="GET",
            headers=headers,
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_list_managed_clusters(self):
        """Test case for list_managed_clusters

        Query your clusters for more details.
        """
        headers = {
            "Accept": "application/json",
        }
        response = self.client.open(
            "/cluster.open-cluster-management.io/v1/managedclusters",
            method="GET",
            headers=headers,
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
