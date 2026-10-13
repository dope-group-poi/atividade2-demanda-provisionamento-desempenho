# Deploy na VM (VirtualBox) e cenarios de provisionamento

> Segue o roteiro da Atividade 2 (VirtualBox do LCC3): VDI pre-configurada,
> rede **NAT + redirecionamento de portas** e acesso pelo host via `localhost`.

## 1. Criar a VM a partir da VDI pre-configurada

1. Copie a imagem para `/tmp` (importante usar o `/tmp`):

   ```bash
   cp /local/uasc/images/ubuntu_serve_2204_poi.vdi /tmp/
   ```

2. No VirtualBox > **Novo**:
   - Nome a escolha; **Pasta da maquina: `/tmp`**.
   - Tipo: *Linux* / Versao: *Ubuntu 22.04 LTS (64-bit)*.
   - Hardware: comece com **1 CPU e 1024 MB** (cenario base).
   - Disco: **Utilizar um disco rigido virtual existente** > aponte para
     `/tmp/ubuntu_serve_2204_poi.vdi`.
   - Finalize.

3. Inicialize a VM e faca login:
   - login: `osboxes`
   - senha: `osboxes.org`

## 2. (Opcional) Smoke test de rede com nginx

Serve so para validar o redirecionamento de portas antes de subir as apps.

```bash
sudo apt update && sudo apt install -y nginx
sudo systemctl status nginx
curl localhost:80            # dentro da VM: deve responder
```

No host, `http://localhost:80` **ainda falha** (ERR_CONNECTION_REFUSED): a maquina
local nao enxerga servicos da VM ate configurar o redirecionamento (secao 3).

## 3. Rede: NAT + redirecionamento de portas

A VM usa **NAT** (padrao). Para o host alcancar as apps, crie regras de
redirecionamento (host -> convidado). Com a VM **desligada**:

VM > Settings > **Rede** > Adaptador 1 (NAT) > Avancado > **Redirecionamento de Portas**.

Crie uma regra por aplicacao (porta do hospedeiro = porta do convidado):

| Nome   | Porta Hospedeiro | IP Convidado | Porta Convidado |
|--------|------------------|--------------|-----------------|
| cpu    | 8001             | (vazio)      | 8001            |
| memory | 8002             | (vazio)      | 8002            |
| io     | 8003             | (vazio)      | 8003            |
| nginx  | 8080             | (vazio)      | 80              |

Equivalente por linha de comando (no host, VM desligada):

```bash
VBoxManage modifyvm "<NOME_DA_VM>" --natpf1 "cpu,tcp,,8001,,8001"
VBoxManage modifyvm "<NOME_DA_VM>" --natpf1 "memory,tcp,,8002,,8002"
VBoxManage modifyvm "<NOME_DA_VM>" --natpf1 "io,tcp,,8003,,8003"
```

Depois de ligar a VM, o host acessa tudo via `http://localhost:<porta>`.
Com nginx (regra acima): `http://localhost:8080` deve mostrar "Welcome to nginx!".

## 4. Preparar a VM (apps POI)

A VDI ja vem com Ubuntu 22.04. Prepare o ambiente das aplicacoes:

```bash
sudo apt update && sudo apt install -y python3-venv git
sudo useradd -r -m -d /opt/poi poi
sudo git clone <URL_DO_REPO> /opt/poi
cd /opt/poi
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
sudo chown -R poi:poi /opt/poi
```

## 5. Configurar e subir a aplicacao (systemd)

Os arquivos `deploy/<app>.env` definem porta e workers. Ajuste `WORKERS`
conforme o cenario (regra pratica: `WORKERS = nº de vCPUs` para cpu/memory; 1 para io).

Instale o servico (exemplo com a cpu_app):

```bash
sudo cp /opt/poi/deploy/poi-app@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now poi-app@cpu_app
sudo systemctl status poi-app@cpu_app
```

Teste dentro da VM: `curl http://localhost:8001/health`
Teste no host (via port forwarding): `curl http://localhost:8001/health`

## 6. Liberar a porta (firewall da VM)

```bash
sudo ufw allow 8001/tcp
```

## 7. Variar o provisionamento entre cenarios

Pare a VM (`sudo poweroff`) e, **no host**, ajuste vCPU/RAM com `VBoxManage`
(ou pela GUI: Settings > System). Use **pelo menos 4 cenarios**:

| Cenario          | vCPU | RAM   | WORKERS |
|------------------|------|-------|---------|
| c1_1vcpu_1gb     | 1    | 1024  | 1       |
| c2_1vcpu_2gb     | 1    | 2048  | 1       |
| c3_2vcpu_2gb     | 2    | 2048  | 2       |
| c4_2vcpu_4gb     | 2    | 4096  | 2       |

```bash
VBoxManage modifyvm "<NOME_DA_VM>" --cpus 2 --memory 2048
```

Depois de ligar a VM, ajuste `WORKERS` no `deploy/<app>.env` e reinicie:

```bash
sudo systemctl restart poi-app@cpu_app
```

## 8. Rodar os experimentos (no host)

Com o redirecionamento de portas, o host fala com a VM por `localhost`.
Para cada cenario, apos reconfigurar a VM:

```bash
APP=cpu URL=http://localhost:8001 SCENARIO=c1_1vcpu_1gb ./experiments/run_scenarios.sh
```

Colete tambem CPU/memoria a nivel de sistema na VM durante a carga
(o `/stats` subreporta com multiplos workers):

```bash
# na VM, em paralelo a cada rodada:
sar -u -r 1 > results/c1_1vcpu_1gb_sar.txt
# ou: vmstat 1
```

Ao final: `python analysis/plot.py --results results/cpu`

## 9. Documentar e salvar o disco

- Capture screenshots de cada etapa (criacao da VM, port forwarding, apps em
  execucao, testes de stress) para a documentacao.
- Salve o disco da VM e guarde em um diretorio do drive (nao esqueca de
  responder o formulario no classroom).
