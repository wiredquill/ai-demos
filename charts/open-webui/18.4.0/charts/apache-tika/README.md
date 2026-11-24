tika-helm
=========

We recommend that the Helm chart version is aligned to the version Tika (and subsequently the
version of the [Tika Docker image][]) you want to deploy.
This will ensure that you using a chart version that has been tested against the corresponding
production version. This will also ensure that the documentation and examples for the chart
will work with the version of Tika you are installing.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Installing](#installing)
  - [Install released version from Helm OCI registry](#install-released-version-from-helm-oci-registry)
  - [Custom configuration for tika](#custom-configuration-for-tika)
- [Upgrading](#upgrading)
- [Values](#values)
- [Testing](#testing)
- [Contributing](#contributing)
- [More Information](#more-information)
- [License](#license)
- [Maintainers](#maintainers)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- Use this to update TOC: -->

## Installing

### Install released version from Helm OCI registry

Charts are published to [Application Collection OCI repository](https://apps.rancher.io). Install directly from the OCI registry (Helm 3.8+).

**N.B.** You may or may not need/wish to install the chart into a specific **namespace**,
in which case you may need to augment the commands below.

* Install from OCI (replace `<version>` with the chart version you want, e.g. `3.2.3`):
  - with Helm 3: `helm install [RELEASE_NAME] oci://dp.apps.rancher.io/charts/apache-tika --version <version> --set image.tag=<app-version> -n tika-test`
  - Example:

    ```console
    helm install [RELEASE_NAME] oci://dp.apps.rancher.io/charts/apache-tika --version 3.2.3 -n tika-test
    ```

* **Chart.yaml dependencies:** Helm appends `name` to `repository`. Set `repository` to the OCI registry URL:

    ```yaml
    dependencies:
      - name: tika
        version: "<version>"
        repository: "oci://dp.rancher.io/containers/apache-tika"
    ```

    Then `helm dependency update`.

    Example installation notes:

    ```text
    NAME: tika
    LAST DEPLOYED: Mon Jan 24 13:38:01 2022
    NAMESPACE: tika-test
    STATUS: deployed
    REVISION: 1
    NOTES:
    1. Get the application URL by running these commands:
      export POD_NAME=$(kubectl get pods --namespace tika-test -l "app.kubernetes.io/name=tika,app.kubernetes.io/instance=tika" -o jsonpath="{.items[0].metadata.name}")
      export CONTAINER_PORT=$(kubectl get pod --namespace tika-test $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
      echo "Visit http://127.0.0.1:9998 to use your application"
      kubectl --namespace tika-test port-forward $POD_NAME 9998:$CONTAINER_PORT
    ```

You may notice that the _kubectl port forwarding_ experiences a _timeout issue_ which ultimately kills the app. In this case you can run port forwarding in a loop:

```console
while true; do kubectl --namespace tika-test port-forward $POD_NAME 9998:$CONTAINER_PORT ; done
```

This should keep `kubectl` reconnecting on connection lost.

### Custom configuration for tika

To use custom [configuration]( https://tika.apache.org/2.9.1/configuring.html) values for apache tika, use the `tikaConfig` key in the `values.yaml`.
Example:

```
tikaConfig: |
  <?xml version="1.0" encoding="UTF-8"?>
  <properties>
    <mtrandata>
      <mime-table-path>/tika-config/custom-mimetypes.xml</mime-table-path>
    </mtrandata>
    <parsers>
      <!-- Default Parser for most things, except for 2 mime types -->
      <parser class="org.apache.tika.parser.DefaultParser">
        <mime-exclude>image/jpeg</mime-exclude>
        <mime-exclude>application/pdf</mime-exclude>
      </parser>
    </parsers>
  </properties>

additionalConfigs:
  custom-mimetypes.xml: |
    <?xml version="1.0" encoding="UTF-8"?>
    <mime-info>
      <mime-type type="application/pdf">
        <magic priority="80">
          <match value="%PDF-" type="string" offset="0:8192"/>
        </magic>
        <glob pattern="*.pdf"/>
      </mime-type>
    </mime-info>
```

## Testing

```
helm plugin install https://github.com/helm-unittest/helm-unittest.git
helm unittest .
```

See [helm-unittest][] for canonical documentation.

## Contributing

Please check [CONTRIBUTING][] before any contribution or for any questions
about our development and testing process.

## More Information

For more infomation on Apache Tika Server, go to the [Apache Tika Server documentation][].

For more information on Apache Tika, go to the official [Apache Tika][] project website.

For more information on the Apache Software Foundation, go to the [Apache Software Foundation][] website.

## License
The code is licensed permissively under the [Apache License v2.0][].

## Maintainers

| Name | Email | Url |
| ---- | ------ | --- |
| SUSE LLC |  | <https://www.suse.com/> |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)

[Apache License v2.0]: https://www.apache.org/licenses/LICENSE-2.0.html
[Apache Software Foundation]: http://apache.org
[Apache Tika]: https://tika.apache.org
[Apache Tika Server documentation]: https://cwiki.apache.org/confluence/display/TIKA/TikaServer
[BREAKING_CHANGES.md]: https://github.com/apache/tika-helm/blob/master/BREAKING_CHANGES.md
[CHANGELOG.md]: https://github.com/apache/tika-helm/blob/master/CHANGELOG.md
[CONTRIBUTING]: https://github.com/apache/tika/blob/main/CONTRIBUTING.md
[helm-unittest]: https://github.com/helm-unittest/helm-unittest
[Tika Docker image]: https://apps.rancher.io/applications/apache-tika
