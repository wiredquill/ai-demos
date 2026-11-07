{{/*
Declared SUSE AI topology (templates/topology.yaml). Same file in
charts/hr-assistant and charts/hr-assistant-vllm; keep the two in step.

The graph follows this chart's values: the three apps, the inference engine
(genai.providerName) and the model they call, and Qdrant / OpenSearch when
they are deployed or pointed at.

The apps, the engine and the databases are declared as the OpenTelemetry
services SUSE Observability creates for them from live telemetry: their
service.name (the apps' OTEL_SERVICE_NAME, the engine's provider name, qdrant,
opensearch) in this release's service.namespace. The SUSE AI Declared Topology
StackPack (1.2.0+) gives them the same identifier,
urn:opentelemetry:namespace/<ns>:service/<name>, so declared and observed
components are one node and the declared relations connect the components the
SUSE AI views show. The model has no such service (SUSE AI tracks model usage
per calling app), so it is a declared component of its own.
*/}}
{{- define "hr-assistant.topologyAttr" -}}
{{- dict "key" (index . 0) "value" (dict "stringValue" (index . 1)) | toJson -}}
{{- end }}

{{/*
OTLP/JSON metrics request for the SUSE AI Declared Topology StackPack: one
suse_ai_declared_component data point per component and one
suse_ai_declared_relation per relation, from scope suse-ai-declared-topology
on a resource marked suse.ai.topology.declared. No service.name, so the
OpenTelemetry StackPack does not turn the sender into a service.
timeUnixNano is set when it is sent (__NOW__). Empty attributes are left out.

Components: type, name, type_name, namespace, product.
Relations: source type and name, target type and name, relation type,
source namespace, target namespace.
*/}}
{{- define "hr-assistant.topologyPayload" -}}
{{- $provider := .Values.genai.providerName -}}
{{- $model := include "hr-assistant.model" . | trim -}}
{{- $ns := include "hr-assistant.serviceNamespace" . | trim -}}
{{- $agents := list "HRAssistant" "HRPolicyDatabase" "EmployeeHandbook" -}}
{{- $components := list -}}
{{- range $agents -}}
{{- $components = append $components (list "agent" . "agent" $ns "") -}}
{{- end -}}
{{- $components = append $components (list "inference-engine" $provider (printf "inference-engine.%s" $provider) $ns $provider) -}}
{{- $components = append $components (list "llm-model" $model (printf "llm-model.%s" $provider) "" "") -}}
{{- $relations := list
  (list "agent" "HRAssistant" "agent" "HRPolicyDatabase" "uses" $ns $ns)
  (list "agent" "HRAssistant" "agent" "EmployeeHandbook" "uses" $ns $ns) -}}
{{- range $agents -}}
{{- $relations = append $relations (list "agent" . "inference-engine" $provider "uses" $ns $ns) -}}
{{- end -}}
{{- $relations = append $relations (list "inference-engine" $provider "llm-model" $model "runs" $ns "") -}}
{{- if or .Values.qdrant.enabled .Values.qdrant.url -}}
{{- $components = append $components (list "vectordb" "qdrant" "vectordb.qdrant" $ns "qdrant") -}}
{{- $relations = append $relations (list "agent" "HRPolicyDatabase" "vectordb" "qdrant" "uses" $ns $ns) -}}
{{- end -}}
{{- if or .Values.opensearch.enabled .Values.opensearch.url -}}
{{- $components = append $components (list "search-engine" "opensearch" "search-engine.opensearch" $ns "opensearch") -}}
{{- $relations = append $relations (list "agent" "HRPolicyDatabase" "search-engine" "opensearch" "uses" $ns $ns) -}}
{{- end -}}
{{- $cpoints := list -}}
{{- range $components -}}
{{- $c := . -}}
{{- $attrs := list -}}
{{- range $i, $key := list "type" "name" "type_name" "namespace" "product" -}}
{{- with index $c $i -}}
{{- $attrs = append $attrs (include "hr-assistant.topologyAttr" (list $key .) | fromJson) -}}
{{- end -}}
{{- end -}}
{{- $cpoints = append $cpoints (dict "asInt" "1" "timeUnixNano" "__NOW__" "attributes" $attrs) -}}
{{- end -}}
{{- $rpoints := list -}}
{{- range $relations -}}
{{- $r := . -}}
{{- $attrs := list -}}
{{- range $i, $key := list "source.type" "source.name" "target.type" "target.name" "type" "source.namespace" "target.namespace" -}}
{{- with index $r $i -}}
{{- $attrs = append $attrs (include "hr-assistant.topologyAttr" (list $key .) | fromJson) -}}
{{- end -}}
{{- end -}}
{{- $rpoints = append $rpoints (dict "asInt" "1" "timeUnixNano" "__NOW__" "attributes" $attrs) -}}
{{- end -}}
{{- $resource := list (include "hr-assistant.topologyAttr" (list "suse.ai.topology.declared" "true") | fromJson) (include "hr-assistant.topologyAttr" (list "k8s.namespace.name" .Release.Namespace) | fromJson) -}}
{{- with dig "cattle" "clusterName" "" (.Values.global | default dict) -}}
{{- $resource = append $resource (include "hr-assistant.topologyAttr" (list "k8s.cluster.name" .) | fromJson) -}}
{{- end -}}
{{- toJson (dict "resourceMetrics" (list (dict
  "resource" (dict "attributes" $resource)
  "scopeMetrics" (list (dict
    "scope" (dict "name" "suse-ai-declared-topology" "version" .Chart.Version)
    "metrics" (list
      (dict "name" "suse_ai_declared_component" "gauge" (dict "dataPoints" $cpoints))
      (dict "name" "suse_ai_declared_relation" "gauge" (dict "dataPoints" $rpoints)))))))) -}}
{{- end }}

{{/*
Pod spec shared by the topology Job and CronJob.
*/}}
{{- define "hr-assistant.topologyPodSpec" -}}
restartPolicy: OnFailure
automountServiceAccountToken: false
securityContext:
  runAsNonRoot: true
  runAsUser: 65534
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: push
    image: {{ .Values.topology.image | quote }}
    command: ["/bin/sh", "/topology/push.sh"]
    env:
      - name: OTLP_ENDPOINT
        value: {{ include "hr-assistant.otlpEndpoint" . | trim | trimSuffix "/" | quote }}
    volumeMounts:
      - name: topology
        mountPath: /topology
        readOnly: true
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
    resources:
      {{- toYaml .Values.topology.resources | nindent 6 }}
volumes:
  - name: topology
    configMap:
      name: {{ include "hr-assistant.fullname" . }}-topology
{{- end }}
