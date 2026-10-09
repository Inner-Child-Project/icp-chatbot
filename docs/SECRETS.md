# Secretos (SOPS + age) — reglas de este repo

- `.env.sops` es la ÚNICA fuente versionada de secretos. Valores cifrados,
  nombres visibles (`git log -p` dice QUÉ rotó, nunca el valor).
- `.env` (plaintext) NUNCA se commitea: el hook `scripts/git-hooks/pre-commit`
  lo bloquea (instalado en `.git/hooks/`).
- Clave age del owner: `~/.config/sops/age/keys.txt` (600). **Copia de
  respaldo en el gestor de contraseñas YA** — sin ella, `.env.sops` es ruido.
- Editar: `./scripts/sops-env.sh edit`. Verificar: `./scripts/sops-env.sh verify`.
- Rotar un valor: `edit`, cambiar, salir (re-cifra solo), commit, redeploy.
- Portainer: el stack NO puede descifrar — los valores van en el env del
  stack (recreate con el editor) o, en Dokploy futuro, vía API del panel.
  `.env.sops` es_registry auditable_, no mecanismo de inyección.
- Revocar acceso = quitar recipient de `.sops.yaml` + `sops updatekeys` +
  ROTAR los secretos (el acceso pasado no se revoca).
