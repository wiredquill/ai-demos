{{/*
Expand the name of the chart.
*/}}
{{- define "llm-comm-upstream.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}