{{- define "topology.fullname" -}}
{{- printf "%s-topology" .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "topology.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}

{{- define "topology.clusterName" -}}
{{- .Values.clusterName | default (dig "cattle" "clusterName" "" (.Values.global | default dict)) -}}
{{- end }}

{{- define "topology.attr" -}}
{{- dict "key" (index . 0) "value" (dict "stringValue" (index . 1)) | toJson -}}
{{- end }}

{{/*
OTLP/JSON metrics request for the SUSE AI Declared Topology StackPack: one
suse_ai_declared_component data point per component and one
suse_ai_declared_relation data point per relation, from scope
suse-ai-declared-topology on a resource marked suse.ai.topology.declared.
No service.name, so the OpenTelemetry StackPack does not turn the sender into
a service. timeUnixNano is set when the payload is sent (__NOW__).
*/}}
{{- define "topology.payload" -}}
{{- $types := dict -}}
{{- $components := list -}}
{{- range .Values.topology.components -}}
{{- $name := tpl .name $ -}}
{{- $_ := set $types $name .type -}}
{{- $attrs := list (include "topology.attr" (list "type" .type) | fromJson) (include "topology.attr" (list "name" $name) | fromJson) (include "topology.attr" (list "type_name" (.typeName | default .type)) | fromJson) -}}
{{- $components = append $components (dict "asInt" "1" "timeUnixNano" "__NOW__" "attributes" $attrs) -}}
{{- end -}}
{{- $relations := list -}}
{{- range .Values.topology.relations -}}
{{- $source := tpl .source $ -}}
{{- $target := tpl .target $ -}}
{{- $sourceType := required (printf "topology.relations: unknown source component %q" $source) (get $types $source) -}}
{{- $targetType := required (printf "topology.relations: unknown target component %q" $target) (get $types $target) -}}
{{- $attrs := list (include "topology.attr" (list "source.type" $sourceType) | fromJson) (include "topology.attr" (list "source.name" $source) | fromJson) (include "topology.attr" (list "target.type" $targetType) | fromJson) (include "topology.attr" (list "target.name" $target) | fromJson) (include "topology.attr" (list "type" .type) | fromJson) -}}
{{- $relations = append $relations (dict "asInt" "1" "timeUnixNano" "__NOW__" "attributes" $attrs) -}}
{{- end -}}
{{- $resource := list (include "topology.attr" (list "suse.ai.topology.declared" "true") | fromJson) (include "topology.attr" (list "k8s.namespace.name" (.Values.namespace | default .Release.Namespace)) | fromJson) -}}
{{- with include "topology.clusterName" . -}}
{{- $resource = append $resource (include "topology.attr" (list "k8s.cluster.name" .) | fromJson) -}}
{{- end -}}
{{- toJson (dict "resourceMetrics" (list (dict
  "resource" (dict "attributes" $resource)
  "scopeMetrics" (list (dict
    "scope" (dict "name" "suse-ai-declared-topology" "version" .Chart.Version)
    "metrics" (list
      (dict "name" "suse_ai_declared_component" "gauge" (dict "dataPoints" $components))
      (dict "name" "suse_ai_declared_relation" "gauge" (dict "dataPoints" $relations)))))))) -}}
{{- end }}

{{/*
Pod spec shared by the install/upgrade Job and the refresh CronJob.
*/}}
{{- define "topology.podSpec" -}}
restartPolicy: OnFailure
automountServiceAccountToken: false
securityContext:
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: push
    image: {{ .Values.image | quote }}
    command: ["/bin/sh", "/topology/push.sh"]
    env:
      - name: OTLP_ENDPOINT
        value: {{ trimSuffix "/" .Values.otlpEndpoint | quote }}
    volumeMounts:
      - name: topology
        mountPath: /topology
        readOnly: true
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 65534
      capabilities:
        drop: ["ALL"]
    resources:
      {{- toYaml .Values.resources | nindent 6 }}
volumes:
  - name: topology
    configMap:
      name: {{ include "topology.fullname" . }}
{{- end }}
