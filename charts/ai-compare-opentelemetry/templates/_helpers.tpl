{{/*
Expand the name of the chart.
*/}}
{{- define "ai-compare-opentelemetry.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ai-compare-opentelemetry.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- if eq .Release.Name "ai-compare" -}}
{{- printf "ai-compare" | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ai-compare-opentelemetry.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "ai-compare-opentelemetry.labels" -}}
helm.sh/chart: {{ include "ai-compare-opentelemetry.chart" . }}
{{ include "ai-compare-opentelemetry.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
observability.opentelemetry.io/enabled: "true"
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "ai-compare-opentelemetry.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ai-compare-opentelemetry.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Compute the OTLP HTTP endpoint (4318) for app telemetry.
When collector.operator.enabled is true, point at the operator-managed
per-namespace collector service; otherwise fall back to the configured endpoint.
*/}}
{{- define "ai-compare-opentelemetry.otlpHttpEndpoint" -}}
{{- if .Values.collector.operator.enabled -}}
http://{{ .Values.collector.operator.name }}-collector.{{ .Release.Namespace }}.svc.cluster.local:4318
{{- else -}}
{{ .Values.aiCompare.observability.otlpEndpoint }}
{{- end -}}
{{- end -}}

{{/*
Compute the OTLP gRPC endpoint (4317) for Open WebUI telemetry.
*/}}
{{- define "ai-compare-opentelemetry.otlpGrpcEndpoint" -}}
{{- if .Values.collector.operator.enabled -}}
http://{{ .Values.collector.operator.name }}-collector.{{ .Release.Namespace }}.svc.cluster.local:4317
{{- else -}}
{{ .Values.openWebui.observability.otlpEndpoint }}
{{- end -}}
{{- end -}}
