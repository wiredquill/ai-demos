{{/*
Expand the name of the chart.
*/}}
{{- define "rancher-ai-ollama.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "rancher-ai-ollama.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "rancher-ai-ollama.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "rancher-ai-ollama.labels" -}}
helm.sh/chart: {{ include "rancher-ai-ollama.chart" . }}
{{ include "rancher-ai-ollama.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "rancher-ai-ollama.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rancher-ai-ollama.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
The list of Ollama models to pull, derived from primary + extras, as a
comma-separated string (split with splitList "," in templates).
*/}}
{{- define "rancher-ai-ollama.modelList" -}}
{{- $models := list .Values.ollama.models.primary -}}
{{- if .Values.ollama.models.extra -}}
{{- range $m := splitList "," .Values.ollama.models.extra -}}
{{- $m = trim $m -}}
{{- if $m -}}
{{- $models = append $models $m -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- join "," $models -}}
{{- end -}}

{{/*
LiteLLM master key: explicit value > existing secret > generated.
*/}}
{{- define "rancher-ai-ollama.litellmMasterKey" -}}
{{- if .Values.litellm.masterkey -}}
{{- .Values.litellm.masterkey -}}
{{- else -}}
{{- $name := printf "%s-litellm-masterkey" (include "rancher-ai-ollama.fullname" .) -}}
{{- $secret := lookup "v1" "Secret" .Release.Namespace $name -}}
{{- if $secret -}}
{{- index $secret.data "masterkey" | b64dec -}}
{{- else -}}
{{- randAlphaNum 32 -}}
{{- end -}}
{{- end -}}
{{- end -}}
