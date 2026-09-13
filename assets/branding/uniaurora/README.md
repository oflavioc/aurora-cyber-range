# UniAurora — Universidade Aurora

Proposta de identidade institucional **v0.1**, criada a pedido do mantenedor para a universidade fictícia. Deriva da família visual do Aurora Cyber Range: símbolo angular em forma de A, faixa de aurora e transição entre ciano, azul e violeta.

O lettering foi simplificado para uma apresentação institucional. A marca Aurora Cyber Range continua identificando a plataforma; UniAurora identifica a universidade dentro da ficção.

## Versões entregues

| Arquivo | Aplicação proposta | Formato |
| --- | --- | --- |
| [uniaurora-logo-light-v0.1.png](uniaurora-logo-light-v0.1.png) | Documentos e placas de fundo claro | PNG RGB, 1536 × 1024, fundo claro incorporado |
| [uniaurora-logo-dark-v0.1.png](uniaurora-logo-dark-v0.1.png) | Placas e peças de fundo azul escuro | PNG RGB, 1536 × 1024, fundo escuro incorporado |

![UniAurora — versão clara](uniaurora-logo-light-v0.1.png)

![UniAurora — versão escura](uniaurora-logo-dark-v0.1.png)

Os PNGs são imagens rasterizadas e opacas. Não são vetores nem texturas transparentes. As duas versões foram geradas visualmente; para produção que exija geometria idêntica, cores exatas ou recorte transparente, será necessário preparar derivados próprios. O lettering está incorporado às imagens; nenhum arquivo de fonte acompanha este conjunto.

## Paleta de trabalho proposta

Os valores abaixo são novas escolhas de implementação inspiradas nos originais. Não foram fornecidos como códigos oficiais da marca Aurora Cyber Range, e não afirmam correspondência exata com cada pixel das imagens geradas.

| Cor | HEX | Papel proposto |
| --- | --- | --- |
| Azul institucional | `#07172E` | Texto principal em fundo claro e placas escuras |
| Ciano | `#00CFF5` | Faixa de aurora e pequenos destaques |
| Azul | `#2475FF` | Transição do símbolo e elementos de apoio |
| Violeta | `#7B41F5` | Acento e fechamento do gradiente |
| Branco frio | `#F5FAFF` | Texto em fundo escuro e superfícies de apoio |

[palette.json](palette.json) fornece os mesmos valores para implementação.

## Aplicação no ambiente universitário

- Usar UniAurora para identificar a instituição em placas da secretaria, recepção, documentos fictícios e telas institucionais.
- Preservar o ambiente realista de uma faculdade: cores neutras, materiais cotidianos e iluminação natural. Ciano e violeta são acentos da marca, não uma exigência de iluminar todo o campus com neon.
- Manter as ações do jogo em linguagem comum, como “Conversar”, “Ler” e “Abrir”, com indicação contextual junto à pessoa ou ao objeto.
- Usar a proporção original, sem esticar ou comprimir. Manter espaço livre ao redor do conjunto.
- Não colocar mensagens, ícones ou objetos por cima do lettering. Escolher a versão conforme a superfície e conferir legibilidade no tamanho real de uso.
- Para painéis sobrepostos e letreiros recortados em 3D, os PNGs opacos são referência de aparência; não pressupor canal alfa ou modelo tridimensional.

As propostas de aplicação não alteram o cenário M01-R6 nem substituem sua especificação. Esta entrega contém identidade visual, não implementação de uma universidade navegável.

## Origem e rastreabilidade

Criada com geração de imagem por IA, usando os logotipos e o símbolo do [Aurora Cyber Range](../aurora-cyber-range/README.md) enviados pelo mantenedor. Os originais permanecem intactos.

O [manifesto](manifest.json) registra tamanhos, dimensões, modo de cor e hashes dos dois PNGs. [GENERATION.md](GENERATION.md) contém as instruções de geração e a distinção entre referência, proposta e arquivos finais.
