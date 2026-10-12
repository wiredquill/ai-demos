{{/*
Expand the name of the chart.
*/}}
{{- define "ai-compare-suse.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ai-compare-suse.fullname" -}}
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
{{- define "ai-compare-suse.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "ai-compare-suse.labels" -}}
helm.sh/chart: {{ include "ai-compare-suse.chart" . }}
{{ include "ai-compare-suse.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "ai-compare-suse.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ai-compare-suse.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Backend URLs. Each backend is either deployed by this chart (<x>.enabled=true,
the in-chart Service) or provided externally, e.g. by the Ollama / Open WebUI /
Pipelines charts deployed as separate AI Factory blueprint components (<x>.url).
*/}}
{{- define "ai-compare-suse.ollamaUrl" -}}
{{- if .Values.ollama.enabled -}}
http://ollama-service:11434
{{- else -}}
{{ .Values.ollama.url | default "http://ollama-service:11434" }}
{{- end -}}
{{- end }}

{{- define "ai-compare-suse.openWebuiUrl" -}}
{{- if .Values.openWebui.enabled -}}
http://open-webui-service:8080
{{- else -}}
{{ .Values.openWebui.url | default "http://open-webui:80" }}
{{- end -}}
{{- end }}

{{- define "ai-compare-suse.pipelinesUrl" -}}
{{- if .Values.pipelines.enabled -}}
http://pipelines-service:9099
{{- else -}}
{{ .Values.pipelines.url | default "http://pipelines-service:9099" }}
{{- end -}}
{{- end }}

{{/*
Image pull secrets: .Values.imagePullSecrets plus global.imagePullSecrets, which
is how SUSE AI Factory hands its delivered pull secret to every component
(including charts that vendor this one as a subchart). Duplicates are dropped.
*/}}
{{- define "ai-compare-suse.imagePullSecrets" -}}
{{- $global := (.Values.global | default dict).imagePullSecrets | default list -}}
{{- toYaml (concat (.Values.imagePullSecrets | default list) $global | uniq) -}}
{{- end }}
