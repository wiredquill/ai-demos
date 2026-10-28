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
{{- include "hermes-openshell.withRules" (dict "root" . "policy" $p) -}}
{{- end -}}

{{/* A profile's policy as is, or, with observability or cluster access on,
     plus their network rules. Re-serialised then, so the file's comments go.
       otel-collector: the venv's python (the real path; OpenShell matches it)
         may send OTLP to the collector.
       cluster-api: kubectl may reach the API server. tls: skip, because the
         supervisor re-encrypts inspected traffic and doesn't trust the cluster
         CA (OpenShell 0.1.5's Kubernetes driver can't add one), so there is no
         method filtering here: the ServiceAccount's RBAC is the limit. */}}
{{- define "hermes-openshell.withRules" -}}
{{- $v := .root.Values -}}
{{- $rules := dict -}}
{{- if $v.observability.enabled -}}
{{- $u := urlParse (include "hermes-openshell.otlpEndpoint" .root) -}}
{{- $port := ternary "443" "80" (eq $u.scheme "https") -}}
{{- $hp := splitList ":" $u.host -}}
{{- if gt (len $hp) 1 }}{{ $port = last $hp }}{{ end -}}
{{- $endpoint := dict "host" $u.hostname "port" (atoi $port) "protocol" "rest" "access" "read-write" "enforcement" "enforce" -}}
{{- $_ := set $rules "otel-collector" (dict "name" "otel-collector" "endpoints" (list $endpoint) "binaries" (list (dict "path" "/usr/bin/python3.13"))) -}}
{{- end -}}
{{- if $v.platform.enabled -}}
{{- $endpoint := dict "host" "kubernetes.default.svc.cluster.local" "port" 443 "tls" "skip" -}}
{{- $_ := set $rules "cluster-api" (dict "name" "cluster-api" "endpoints" (list $endpoint) "binaries" (list (dict "path" "/usr/local/bin/kubectl"))) -}}
{{- end -}}
{{- if not $rules -}}
{{- .policy -}}
{{- else -}}
{{- $p := fromYaml .policy -}}
{{- $p = set $p "network_policies" (merge $rules ($p.network_policies | default dict)) -}}
{{- toYaml $p -}}
{{- end -}}
{{- end -}}

{{/* Cluster access settings; fails on what isn't built yet. */}}
{{- define "hermes-openshell.platform" -}}
{{- $pl := .Values.platform -}}
{{- if not (has $pl.access (list "view" "operator")) -}}
{{- fail (printf "unknown platform.access %q (view or operator)" $pl.access) -}}
{{- end -}}
{{- if ne $pl.via "kubernetes" -}}
{{- fail (printf "platform.via %q isn't supported yet (kubernetes)" $pl.via) -}}
{{- end -}}
{{- $name := $pl.clusterName | default (dig "cattle" "clusterName" "" (.Values.global | default dict)) | default .Release.Namespace -}}
{{- dict "access" $pl.access "clusterName" $name "serviceAccount" (printf "%s-platform" (include "hermes-openshell.fullname" .)) | toJson -}}
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
