{{/*
Expand the name of the chart.
*/}}
{{- define "ai-compare.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}