{{/*
Expand the name of the chart.
*/}}
{{- define "stable-diffusion.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "stable-diffusion.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "stable-diffusion.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "stable-diffusion.labels" -}}
helm.sh/chart: {{ include "stable-diffusion.chart" . }}
{{ include "stable-diffusion.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "stable-diffusion.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stable-diffusion.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Get the UI variant image
*/}}
{{- define "stable-diffusion.image" -}}
{{- if eq .Values.uiVariant "comfyui" }}
{{- printf "%s:%s" .Values.comfyui.image.repository .Values.comfyui.image.tag }}
{{- else if eq .Values.uiVariant "automatic1111" }}
{{- printf "%s:%s" .Values.automatic1111.image.repository .Values.automatic1111.image.tag }}
{{- else if eq .Values.uiVariant "invokeai" }}
{{- printf "%s:%s" .Values.invokeai.image.repository .Values.invokeai.image.tag }}
{{- end }}
{{- end }}

{{/*
Get the service port based on UI variant
*/}}
{{- define "stable-diffusion.servicePort" -}}
{{- if eq .Values.uiVariant "comfyui" }}
{{- .Values.comfyui.service.port }}
{{- else if eq .Values.uiVariant "automatic1111" }}
{{- .Values.automatic1111.service.port }}
{{- else if eq .Values.uiVariant "invokeai" }}
{{- .Values.invokeai.service.port }}
{{- end }}
{{- end }}

{{/*
Get the service type based on UI variant
*/}}
{{- define "stable-diffusion.serviceType" -}}
{{- if eq .Values.uiVariant "comfyui" }}
{{- .Values.comfyui.service.type }}
{{- else if eq .Values.uiVariant "automatic1111" }}
{{- .Values.automatic1111.service.type }}
{{- else if eq .Values.uiVariant "invokeai" }}
{{- .Values.invokeai.service.type }}
{{- end }}
{{- end }}

{{/*
Get the nodePort based on UI variant
*/}}
{{- define "stable-diffusion.nodePort" -}}
{{- if eq .Values.uiVariant "comfyui" }}
{{- .Values.comfyui.service.nodePort }}
{{- else if eq .Values.uiVariant "automatic1111" }}
{{- .Values.automatic1111.service.nodePort }}
{{- else if eq .Values.uiVariant "invokeai" }}
{{- .Values.invokeai.service.nodePort }}
{{- end }}
{{- end }}

{{/*
Get the model PVC name
*/}}
{{- define "stable-diffusion.modelsPvcName" -}}
{{- if .Values.storage.models.existingClaim }}
{{- .Values.storage.models.existingClaim }}
{{- else }}
{{- printf "%s-models-pvc" (include "stable-diffusion.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Get the outputs PVC name
*/}}
{{- define "stable-diffusion.outputsPvcName" -}}
{{- if .Values.storage.outputs.existingClaim }}
{{- .Values.storage.outputs.existingClaim }}
{{- else }}
{{- printf "%s-outputs-pvc" (include "stable-diffusion.fullname" .) }}
{{- end }}
{{- end }}
