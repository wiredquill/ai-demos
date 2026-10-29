{{- define "hermes-rancher.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* The client Deployment and its pod (<release>-client-...): the openshell CLI
     that creates the sandbox and forwards its UI. The sandbox pod, with the
     OpenShell supervisor, is named after the sandbox (sandbox.name). */}}
{{- define "hermes-rancher.clientName" -}}
{{- printf "%s-client" (include "hermes-rancher.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "hermes-rancher.labels" -}}
app.kubernetes.io/name: hermes-rancher
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "hermes-rancher.selector" -}}
app.kubernetes.io/name: hermes-rancher
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* The image the sandbox runs, from the form's dropdown. */}}
{{- define "hermes-rancher.sandboxImage" -}}
{{- if eq .Values.sandbox.image "custom" -}}
{{- required "sandbox.customImage is required when sandbox.image is custom" .Values.sandbox.customImage -}}
{{- else -}}
{{- required (printf "unknown sandbox.image %q (suse or custom)" .Values.sandbox.image) (get .Values.sandbox.images .Values.sandbox.image) -}}
{{- end -}}
{{- end -}}

{{/* The selected profile's policy file; fails on an unknown profile. */}}
{{- define "hermes-rancher.policy" -}}
{{- $f := printf "profiles/%s.yaml" .Values.profile -}}
{{- $p := .Files.Get $f -}}
{{- if not $p -}}
{{- fail (printf "unknown profile %q (lockdown, research, developer or dangerous)" .Values.profile) -}}
{{- end -}}
{{- include "hermes-rancher.withRules" (dict "root" . "policy" $p) -}}
{{- end -}}

{{/* A profile's policy plus this chart's network rules. Re-serialised, so
     the file's comments go.
       otel-collector: the venv's python (the real path; OpenShell matches it)
         may send OTLP to the collector.
       cluster-api: kubectl may reach the API server. tls: skip, because the
         supervisor re-encrypts inspected traffic and doesn't trust the cluster
         CA (OpenShell 0.1.5's Kubernetes driver can't add one), so there is no
         method filtering here: the ServiceAccount's RBAC is the limit. (The
         planned Rancher route needs no skip: Rancher's certificate is
         publicly trusted, so OpenShell can inspect it and inject the token.) */}}
{{- define "hermes-rancher.withRules" -}}
{{- $v := .root.Values -}}
{{- $rules := dict -}}
{{- if $v.observability.enabled -}}
{{- $u := urlParse (include "hermes-rancher.otlpEndpoint" .root) -}}
{{- $port := ternary "443" "80" (eq $u.scheme "https") -}}
{{- $hp := splitList ":" $u.host -}}
{{- if gt (len $hp) 1 }}{{ $port = last $hp }}{{ end -}}
{{- $endpoint := dict "host" $u.hostname "port" (atoi $port) "protocol" "rest" "access" "read-write" "enforcement" "enforce" -}}
{{- $_ := set $rules "otel-collector" (dict "name" "otel-collector" "endpoints" (list $endpoint) "binaries" (list (dict "path" "/usr/bin/python3.13"))) -}}
{{- end -}}
{{- if eq $v.platform.via "kubernetes" -}}
{{- $endpoint := dict "host" "kubernetes.default.svc.cluster.local" "port" 443 "tls" "skip" -}}
{{- $_ := set $rules "cluster-api" (dict "name" "cluster-api" "endpoints" (list $endpoint) "binaries" (list (dict "path" "/usr/local/bin/kubectl") (dict "path" "/usr/local/bin/helm"))) -}}
{{- end -}}
{{- $p := fromYaml .policy -}}
{{- $p = set $p "network_policies" (merge $rules ($p.network_policies | default dict)) -}}
{{- toYaml $p -}}
{{- end -}}

{{/* Cluster access settings; fails on what isn't built yet. */}}
{{- define "hermes-rancher.platform" -}}
{{- $pl := .Values.platform -}}
{{- if not (has $pl.access (list "view" "operator")) -}}
{{- fail (printf "unknown platform.access %q (view or operator)" $pl.access) -}}
{{- end -}}
{{- $name := $pl.clusterName | default (dig "cattle" "clusterName" "" (.Values.global | default dict)) | default .Release.Namespace -}}
{{- $out := dict "access" $pl.access "via" $pl.via "clusterName" $name "serviceAccount" (printf "%s-platform" (include "hermes-rancher.fullname" .)) -}}
{{- if eq $pl.via "rancher" -}}
{{- $u := urlParse (required "platform.rancher.url is required when platform.via is rancher" $pl.rancher.url) -}}
{{- if ne $u.scheme "https" -}}
{{- fail (printf "platform.rancher.url %q must be https" $pl.rancher.url) -}}
{{- end -}}
{{- $_ := set $out "rancherUrl" (printf "https://%s" $u.host) -}}
{{- $_ := set $out "rancherHost" $u.hostname -}}
{{- $_ := set $out "rancherSecret" (required "platform.rancher.existingSecret is required when platform.via is rancher" $pl.rancher.existingSecret) -}}
{{- else if ne $pl.via "kubernetes" -}}
{{- fail (printf "unknown platform.via %q (kubernetes or rancher)" $pl.via) -}}
{{- end -}}
{{- $out | toJson -}}
{{- end -}}

{{/* The model backend's settings: url, name, and the Secret holding the key. */}}
{{- define "hermes-rancher.model" -}}
{{- $m := .Values.model -}}
{{- if eq $m.backend "vllm" -}}
{{- dict "url" $m.vllm.url "name" $m.vllm.name "secret" "" | toJson -}}
{{- else if eq $m.backend "external" -}}
{{- $secret := "" -}}
{{- if $m.external.existingSecret -}}{{- $secret = $m.external.existingSecret -}}
{{- else if $m.external.apiKey -}}{{- $secret = printf "%s-llm" (include "hermes-rancher.fullname" .) -}}
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
{{- define "hermes-rancher.otlpEndpoint" -}}
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
{{- define "hermes-rancher.branding" -}}
{{- $v := .Values -}}
{{- $profile := $v.profile -}}
{{- $out := dict -}}
{{- if $v.hermes.session.enabled -}}
{{- $welcome := printf "%s Approvals: %s." (get $v.hermes.session.welcome $profile) (get $v.approvals $profile) | trim -}}
{{- $p := $v.platform -}}
{{- $welcome = printf "%s Cluster access: %s via %s." $welcome $p.access $p.via -}}
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
{{- define "hermes-rancher.title" -}}
{{- $name := "Hermes for Rancher" -}}
{{- with .Values.hermes.branding -}}
{{- if and .enabled .agentName }}{{ $name = .agentName }}{{ end -}}
{{- end -}}
{{- printf "%s · %s" $name .Values.profile -}}
{{- end -}}
