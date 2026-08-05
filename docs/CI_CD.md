# CI/CD — Deploy automático em produção

O workflow `.github/workflows/deploy.yml` roda `./atualizar_producao.sh`
no servidor de produção via SSH, automaticamente a cada push/merge na
`main`, ou manualmente pela aba **Actions** (botão "Run workflow").

Ele não substitui o script — só o dispara remotamente. O script continua
sendo a fonte de verdade do que acontece no deploy (`git pull`, rebuild
dos containers, checagem de saúde da API).

## Setup (uma vez)

### 1. Gerar um par de chaves SSH dedicado ao deploy

Não reuse sua chave pessoal — gere uma chave só pra isso, sem senha
(o workflow roda sem interação):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

Isso cria `deploy_key` (privada) e `deploy_key.pub` (pública).

### 2. Autorizar a chave pública no servidor

No servidor de produção, adicione o conteúdo de `deploy_key.pub` ao
`~/.ssh/authorized_keys` do usuário que roda o deploy (o mesmo que já
usa `atualizar_producao.sh` manualmente):

```bash
cat deploy_key.pub >> ~/.ssh/authorized_keys
```

Opcional (recomendado) — restrinja essa chave a só rodar o script de
deploy, prefixando a linha em `authorized_keys` com:

```
command="cd /opt/gdconecta/crm && ./atualizar_producao.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA...
```

(ajuste o caminho pro real do servidor). Com isso, mesmo que a chave
vaze, ela só serve pra rodar esse script — não pra abrir um shell livre.

### 3. Cadastrar os Secrets no GitHub

No repositório: **Settings → Secrets and variables → Actions → New
repository secret**. Crie:

| Secret | Valor |
|---|---|
| `PROD_SSH_HOST` | host/IP do servidor (ex.: `crm.gdconecta.com.br`) |
| `PROD_SSH_USER` | usuário SSH usado no deploy |
| `PROD_SSH_KEY` | conteúdo **completo** de `deploy_key` (a privada) |
| `PROD_DEPLOY_PATH` | caminho do projeto no servidor (ex.: `/opt/gdconecta/crm`) |
| `PROD_SSH_PORT` | porta SSH, só se não for 22 (opcional) |

Depois de cadastrar, apague `deploy_key`/`deploy_key.pub` da sua
máquina local (só o servidor e o GitHub Secrets precisam da chave).

### 4. (Opcional, recomendado) Proteger o Environment

Em **Settings → Environments → New environment**, crie um environment
chamado `production` e, se quiser um freio manual antes de cada deploy,
ative **Required reviewers**. O workflow já referencia
`environment: production` — se o environment existir com reviewers
obrigatórios, o deploy fica pausado esperando aprovação antes de rodar.

## Testando

Depois de cadastrar os secrets, vá em **Actions → Deploy em produção →
Run workflow** pra disparar manualmente sem precisar esperar um push na
`main`. Acompanhe o log ali mesmo — ele reflete a saída do
`atualizar_producao.sh` normalmente.
