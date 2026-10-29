{{- define "hermes-openshell.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* The client Deployment and its pod (<release>-client-...): the openshell CLI
     that creates the sandbox and forwards its UI. The sandbox pod, with the
     OpenShell supervisor, is named after the sandbox (sandbox.name). */}}
{{- define "hermes-openshell.clientName" -}}
{{- printf "%s-client" (include "hermes-openshell.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "hermes-openshell.labels" -}}
app.kubernetes.io/name: hermes-openshell
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "hermes-openshell.selector" -}}
app.kubernetes.io/name: hermes-openshell
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* The image the sandbox runs, from the form's dropdown. */}}
{{- define "hermes-openshell.sandboxImage" -}}
{{- if eq .Values.sandbox.image "custom" -}}
{{- required "sandbox.customImage is required when sandbox.image is custom" .Values.sandbox.customImage -}}
{{- else -}}
{{- required (printf "unknown sandbox.image %q (suse, opensuse or custom)" .Values.sandbox.image) (get .Values.sandbox.images .Values.sandbox.image) -}}
{{- end -}}
{{- end -}}

{{/* The selected profile's policy file; fails on an unknown profile. */}}
{{- define "hermes-openshell.policy" -}}
{{- $f := printf "profiles/%s.yaml" .Values.profile -}}
{{- $p := .Files.Get $f -}}
{{- if not $p -}}
{{- fail (printf "unknown profile %q (lockdown, research, developer or dangerous)" .Values.profile) -}}
{{- end -}}
{{- include "hermes-openshell.withOtel" (dict "root" . "policy" $p) -}}
{{- end -}}

{{/* A profile's policy as is, or with observability on, plus a network rule
     that lets the venv's python (the real path; OpenShell matches it) send
     OTLP to the collector. Re-serialised then, so the file's comments go. */}}
{{- define "hermes-openshell.withOtel" -}}
{{- $o := .root.Values.observability -}}
{{- if not $o.enabled -}}
{{- .policy -}}
{{- else -}}
{{- $u := urlParse (include "hermes-openshell.otlpEndpoint" .root) -}}
{{- $port := ternary "443" "80" (eq $u.scheme "https") -}}
{{- $hp := splitList ":" $u.host -}}
{{- if gt (len $hp) 1 }}{{ $port = last $hp }}{{ end -}}
{{- $endpoint := dict "host" $u.hostname "port" (atoi $port) "protocol" "rest" "access" "read-write" "enforcement" "enforce" -}}
{{- $rule := dict "name" "otel-collector" "endpoints" (list $endpoint) "binaries" (list (dict "path" "/usr/bin/python3.13")) -}}
{{- $p := fromYaml .policy -}}
{{- $np := $p.network_policies | default dict -}}
{{- $_ := set $np "otel-collector" $rule -}}
{{- $_ = set $p "network_policies" $np -}}
{{- toYaml $p -}}
{{- end -}}
{{- end -}}

{{/* The model backend's settings: url, name, and the Secret holding the key. */}}
{{- define "hermes-openshell.model" -}}
{{- $m := .Values.model -}}
{{- if eq $m.backend "vllm" -}}
{{- dict "url" $m.vllm.url "name" $m.vllm.name "secret" "" | toJson -}}
{{- else if eq $m.backend "external" -}}
{{- $secret := "" -}}
{{- if $m.external.existingSecret -}}{{- $secret = $m.external.existingSecret -}}
{{- else if $m.external.apiKey -}}{{- $secret = printf "%s-llm" (include "hermes-openshell.fullname" .) -}}
{{- end -}}
{{- dict "url" (required "model.external.url is required" $m.external.url) "name" (required "model.external.name is required" $m.external.name) "secret" $secret | toJson -}}
{{- else -}}
{{- fail (printf "unknown model.backend %q (vllm or external)" $m.backend) -}}
{{- end -}}
{{- end -}}

{{/* OTLP/HTTP endpoint: observability.otlpEndpoint, else the shared SUSE AI
     collector's Service found at install time (as the hr-assistant chart does:
     collectorNamespace, then observability, then suse-observability; a Service
     named *opentelemetry-collector* or labelled so), else the conventional
     name. `lookup` finds nothing under `helm template`. */}}
{{- define "hermes-openshell.otlpEndpoint" -}}
{{- $o := .Values.observability -}}
{{- if $o.otlpEndpoint -}}
{{- $o.otlpEndpoint -}}
{{- else -}}
{{- $found := "" -}}
{{- range $ns := compact (uniq (list $o.collectorNamespace "observability" "suse-observability")) -}}
{{- if not $found -}}
{{- range $svc := ((lookup "v1" "Service" $ns "").items | default list) -}}
{{- if not $found -}}
{{- $name := dig "app.kubernetes.io/name" "" ($svc.metadata.labels | default dict) -}}
{{- if or (contains "opentelemetry-collector" $svc.metadata.name) (eq $name "opentelemetry-collector") -}}
{{- $found = printf "http://%s.%s.svc.cluster.local:4318" $svc.metadata.name $ns -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- $found | default "http://opentelemetry-collector.observability.svc.cluster.local:4318" -}}
{{- end -}}
{{- end -}}

{{/* Hermes's branding text, as {KEY: text} for HERMES_BRANDING_<KEY>: the
     form's branding fields, over the session's words (hermes.session): the
     profile in the prompt and response header, and a welcome line with what
     the profile allows. */}}
{{- define "hermes-openshell.branding" -}}
{{- $v := .Values -}}
{{- $profile := $v.profile -}}
{{- $out := dict -}}
{{- if $v.hermes.session.enabled -}}
{{- $welcome := printf "%s Approvals: %s." (get $v.hermes.session.welcome $profile) (get $v.approvals $profile) | trim -}}
{{- $_ := set $out "WELCOME" (printf "%s Type /help for commands." $welcome) -}}
{{- $_ := set $out "RESPONSE_LABEL" (printf " Hermes · %s " $profile) -}}
{{- $_ := set $out "PROMPT_SYMBOL" (printf "%s ❯" $profile) -}}
{{- end -}}
{{- if $v.hermes.branding.enabled -}}
{{- range $key, $env := dict "agentName" "AGENT_NAME" "welcome" "WELCOME" "goodbye" "GOODBYE" "responseLabel" "RESPONSE_LABEL" "promptSymbol" "PROMPT_SYMBOL" "helpHeader" "HELP_HEADER" -}}
{{- with get $v.hermes.branding $key }}{{ $_ := set $out $env . }}{{ end -}}
{{- end -}}
{{- end -}}
{{- toYaml $out -}}
{{- end -}}

{{/* The browser tab's title: the agent's name and the profile. */}}
{{- define "hermes-openshell.title" -}}
{{- $name := "Hermes in OpenShell" -}}
{{- with .Values.hermes.branding -}}
{{- if and .enabled .agentName }}{{ $name = .agentName }}{{ end -}}
{{- end -}}
{{- printf "%s · %s" $name .Values.profile -}}
{{- end -}}
