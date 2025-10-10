# Comandos Personalizados para Claude Code

## Comandos Git

### /commit
Agrega todos los cambios al staging area y crea un commit con un mensaje descriptivo.

**Ejemplo de uso:**
```
/commit Agrega nueva funcionalidad de autenticación
```

**Comando:**
```bash
git add -A && git commit -m "$ARGS"
```

---

### /push
Envía los commits locales al repositorio remoto en la rama actual.

**Ejemplo de uso:**
```
/push
```

**Comando:**
```bash
git push origin HEAD
```

---

### /commit-push
Agrega todos los cambios, crea un commit y hace push al repositorio remoto en un solo comando.

**Ejemplo de uso:**
```
/commit-push Implementa validación de formularios
```

**Comando:**
```bash
git add -A && git commit -m "$ARGS" && git push origin HEAD
```

---

### /status
Muestra el estado actual del repositorio git.

**Ejemplo de uso:**
```
/status
```

**Comando:**
```bash
git status
```

---

### /log
Muestra el historial de commits de forma compacta.

**Ejemplo de uso:**
```
/log
```

**Comando:**
```bash
git log --oneline --graph --decorate -10
```

---

### /pull
Obtiene y fusiona los cambios del repositorio remoto.

**Ejemplo de uso:**
```
/pull
```

**Comando:**
```bash
git pull origin HEAD
```

---

### /branch
Muestra todas las ramas locales y remotas.

**Ejemplo de uso:**
```
/branch
```

**Comando:**
```bash
git branch -a
```

---

### /diff
Muestra los cambios que aún no han sido agregados al staging area.

**Ejemplo de uso:**
```
/diff
```

**Comando:**
```bash
git diff
```

---

## Notas de Uso

- **$ARGS** representa los argumentos que pasas después del comando
- Asegúrate de estar en un repositorio git inicializado
- Para comandos que requieren autenticación, configura tus credenciales git previamente
- Los comandos se ejecutan en la raíz del proyecto actual

## Configuración Recomendada

Antes de usar estos comandos, asegúrate de tener configurado:

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

Para evitar ingresar credenciales constantemente, considera usar SSH o un credential helper:

```bash
# Para HTTPS con credential helper
git config --global credential.helper store

# O mejor aún, usa SSH
# Genera una clave SSH y agrégala a tu cuenta de GitHub/GitLab
ssh-keygen -t ed25519 -C "tu@email.com"
```