// O BANNER OBRIGATORIO — `05_SECURITY_REQUIREMENTS.md` §4.
//
// *"Em toda tela e no rodape de todo artefato gerado — PDF, historico, diploma,
// relatorio, exportacao, arquivo de evidencia."*
//
// POR QUE UM COMPONENTE, E NAO TRES LITERAIS
// -------------------------------------------
// O texto e NORMATIVO: ele esta num bloco de codigo da spec, e
// `scripts/check_banner_de_simulacao.py` o extrai de la e cobra que este arquivo
// o contenha **exatamente**. Tres copias divergiriam na primeira correcao, e a
// que divergisse em silencio seria a que ninguem esta olhando — a mesma classe
// que a D3 fechou no payload.
//
// O QUE ELE CUSTA NO TELAO, E A CONTA ESTA DECLARADA
// ----------------------------------------------------
// A D16 mediu o orcamento do wallboard em 7 a 8 linhas a 10 m. O banner ocupa
// UMA, e nao e negociavel: `05` §4 nao tem excecao para tela pequena. Ele fica
// no topo, em faixa de largura inteira, para que quem entra na sala o leia antes
// de olhar o indice — e nao no rodape, onde um projetor cortado o esconderia.
//
// A REGRA DE OURO desta fase vale aqui tambem: quem afirma que a tela mostra o
// banner e o VERIFICADOR, e nao esta prosa. Presenca de banner e propriedade do
// DOM, e nao de renderizacao — foi o ponto 4 do auditor, e e por isso que ela
// saiu do limite declarado da §2.2 e virou gate.

/** O texto normativo, LETRA POR LETRA. Alterar aqui sem alterar a spec reprova. */
export const TEXTO_DO_BANNER = "AMBIENTE SIMULADO — DADOS FICTÍCIOS";

/** A faixa. `role="note"` porque ela nao e navegacao nem cabecalho de conteudo. */
export function BannerDeSimulacao() {
  return (
    <div
      role="note"
      className="w-full bg-amber-400 px-[1vw] py-[0.3vw] text-center text-[1.2vw] font-bold uppercase tracking-[0.2em] text-slate-950"
    >
      {TEXTO_DO_BANNER}
    </div>
  );
}
