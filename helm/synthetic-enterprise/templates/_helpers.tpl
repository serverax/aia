{{/* Common labels for a service `name` in the current release context `$`. */}}
{{- define "se.labels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .release }}
app.kubernetes.io/part-of: synthetic-enterprise
app.kubernetes.io/managed-by: {{ .managedBy }}
{{- end -}}

{{/* Selector labels (stable subset). */}}
{{- define "se.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .release }}
{{- end -}}
