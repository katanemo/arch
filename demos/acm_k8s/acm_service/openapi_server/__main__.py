#!/usr/bin/env python3

import connexion

from openapi_server import encoder


def main():
    app = connexion.App(__name__, specification_dir="./openapi/")
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(
        "openapi.yaml",
        arguments={
            "title": "ACM API for cluster management - https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.12/html/apis/apis#tags"
        },
        pythonic_params=True,
    )

    app.run(port=8080)


if __name__ == "__main__":
    main()
