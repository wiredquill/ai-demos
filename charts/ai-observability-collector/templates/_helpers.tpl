{{/*
Name of the collector ServiceAccount and Service (per CR name).
The operator names the collector Service <cr-name>-collector.
*/}}
{{- define "aiobs.collectorService" -}}
{{- printf "%s-collector" .Values.collector.name -}}
{{- end }}

{{/*
Full OTLP HTTP endpoint for auto-instrumented apps / sample app.
*/}}
{{- define "aiobs.otlpHttpEndpoint" -}}
{{- printf "http://%s.%s.svc.cluster.local:4318" (include "aiobs.collectorService" .) .Release.Namespace -}}
{{- end }}

{{/*
Common chart labels.
*/}}
{{- define "aiobs.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
