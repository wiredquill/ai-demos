{{/*
Expand the name of the chart.
*/}}
{{- define "ai-compare-suse.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}