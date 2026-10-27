{{/* "true" when the object passed in (list obj $) was created by this release,
     so upgrades keep rendering it instead of deleting it. */}}
{{- define "agent-sandbox.ownedByRelease" -}}
{{- $obj := index . 0 -}}
{{- $root := index . 1 -}}
{{- $ann := $obj.metadata.annotations | default dict -}}
{{- if and (eq (get $ann "meta.helm.sh/release-name") $root.Release.Name) (eq (get $ann "meta.helm.sh/release-namespace") $root.Release.Namespace) -}}
true
{{- end -}}
{{- end -}}
