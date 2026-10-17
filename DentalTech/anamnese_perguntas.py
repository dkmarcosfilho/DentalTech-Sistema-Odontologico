"""
Catálogo da Anamnese (Prontuário de Odontologia, páginas 9 e 10 da ficha
da Clínica-Escola).

Para mudar uma pergunta, basta editar este arquivo: o formulário, a tela
de leitura e a validação são montados a partir daqui. As respostas ficam
guardadas por CÓDIGO (ex.: "cardio_pressao_alta"), então não troque o
código de uma pergunta que já tem respostas salvas.
"""
from dataclasses import dataclass

# Tipos de item
ESCOLHA = "escolha"      # uma opção (bolinha)
MULTIPLA = "multipla"    # várias opções (caixinhas de marcar)
TEXTO = "texto"          # texto livre

SIM, NAO, NAO_SEI, AS_VEZES = "S", "N", "NS", "AV"

SIM_NAO_NAO_SEI = ((SIM, "Sim"), (NAO, "Não"), (NAO_SEI, "Não sei"))
SIM_NAO = ((SIM, "Sim"), (NAO, "Não"))
SIM_NAO_AS_VEZES = ((SIM, "Sim"), (NAO, "Não"), (AS_VEZES, "Às vezes"))

HORAS = tuple((str(h), str(h)) for h in range(1, 13))


@dataclass(frozen=True)
class Item:
    codigo: str
    texto: str
    tipo: str = ESCOLHA
    opcoes: tuple = SIM_NAO_NAO_SEI
    # Rótulo de um campo de texto que acompanha o item ("A que?", "Qual?").
    # O texto é guardado em "<codigo>_detalhe".
    detalhe: str = ""
    nota: str = ""

    @property
    def codigo_detalhe(self):
        return f"{self.codigo}_detalhe"


@dataclass(frozen=True)
class Secao:
    codigo: str
    titulo: str
    itens: tuple


def _sns(codigo, texto, **kw):
    return Item(codigo, texto, ESCOLHA, SIM_NAO_NAO_SEI, **kw)


def _sn(codigo, texto, **kw):
    return Item(codigo, texto, ESCOLHA, SIM_NAO, **kw)


SECOES = (
    Secao("cardiovascular", "Sistema cardiovascular", (
        _sns("cardio_problema_coracao",
             "Já foi prevenido por algum médico que tem problema no coração?"),
        _sns("cardio_falta_ar",
             "Sente falta de ar ou cansaço após esforço físico ou mesmo em repouso?"),
        _sns("cardio_dor_peito",
             "Sente dor no peito após esforço físico?"),
        _sns("cardio_inchaco",
             "Tem inchaço nas pernas ou nos pés que pioram ao longo do dia?"),
        _sns("cardio_pressao_alta", "Tem pressão alta?"),
    )),
    Secao("respiratorio", "Sistema respiratório", (
        _sns("resp_tosse", "Tosse muito?"),
        _sns("resp_sangue_escarro",
             "Costuma apresentar sangue junto com o escarro?"),
    )),
    Secao("circulatorio", "Sistema circulatório", (
        _sns("circ_sangra_corte", "Sangra muito quando se corta?"),
        _sns("circ_hemorragia",
             "Tem, com frequência, algum tipo de hemorragia?"),
        _sns("circ_anemia", "Já teve anemia?"),
    )),
    Secao("endocrino", "Sistema endócrino", (
        _sns("endo_urina_noite", "Levanta-se muito para urinar à noite?"),
        _sns("endo_sede", "Tem tido muita sede?"),
        _sns("endo_cicatrizacao",
             "Quando se corta, a cicatrização é demorada?"),
        _sns("endo_tireoide", "Tem algum problema de tireoide?"),
        _sns("endo_gravida", "Está grávida?",
             nota="Somente para pacientes do sexo feminino."),
        _sns("endo_anticoncepcional", "Usa algum método anticoncepcional?",
             nota="Somente para pacientes do sexo feminino."),
    )),
    Secao("imunologico", "Sistema imunológico", (
        _sns("imuno_alergia", "Tem algum tipo de alergia?",
             detalhe="A que?"),
        _sns("imuno_alergia_remedio", "Tem alergia a algum remédio?",
             detalhe="Qual?"),
        _sns("imuno_anestesia",
             "Tem ou teve algum problema ao tomar anestesia no dentista?",
             detalhe="Qual?"),
    )),
    Secao("nervoso", "Sistema nervoso / perfil psicológico", (
        _sns("nerv_convulsao", "Já teve convulsão?"),
        _sns("nerv_tratamento_nervos", "Já fez tratamento para os nervos?"),
        _sns("nerv_medicamento_nervos", "Toma medicamento para os nervos?"),
    )),
    Secao("genitourinario", "Sistema genitourinário", (
        _sns("geni_dor_rins", "Tem problema de dores constantes nos rins?"),
        _sns("geni_dor_sangue_urinar",
             "Tem dor e/ou sangramento ao urinar?"),
        _sns("geni_urina_noite", "Levanta-se muito para urinar à noite?"),
    )),
    Secao("digestivo", "Sistema digestivo", (
        _sns("dige_mau_halito", "Tem mau hálito?"),
        _sns("dige_dor_estomago", "Tem dores no estômago frequentemente?"),
        _sns("dige_amarelo", "Já ficou com a pele e os olhos amarelados?"),
        _sns("dige_figado", "Tem algum problema no fígado?"),
    )),
    Secao("osteoarticular", "Sistema osteoarticular", (
        _sns("osteo_dor_articulacoes", "Sente dores nas articulações?"),
        _sns("osteo_febre_reumatica", "Já teve febre reumática?"),
    )),
    Secao("infecciosas", "Doenças infecciosas", (
        _sns("infec_transfusao", "Já recebeu transfusão de sangue?"),
        _sns("infec_drogas", "Fez ou faz uso de drogas?"),
        _sns("infec_conduta_risco", "Teve alguma conduta de risco?"),
        _sns("infec_portador",
             "É / foi portador de alguma doença infectocontagiosa?"),
        Item("infec_quais", "Se sim, marque qual(is):", MULTIPLA, (
            ("tuberculose", "Tuberculose"),
            ("hiv", "HIV positivo"),
            ("herpes", "Herpes simples"),
            ("sifilis", "Sífilis"),
        )),
    )),
    Secao("tratamento_atual", "Tratamento médico atual", (
        _sn("atual_tratamento", "Está fazendo algum tratamento médico?"),
        _sn("atual_medicamento", "Está tomando algum medicamento?"),
    )),
    Secao("tratamento_anterior", "Tratamento médico anterior", (
        _sn("ant_hospitalizado", "Foi hospitalizado nos últimos 2 anos?"),
        _sn("ant_cirurgia", "Foi submetido a alguma cirurgia?"),
    )),
    Secao("antecedentes", "Antecedentes familiares", (
        Item("fam_antecedentes", "Marque o que existe na família:", MULTIPLA, (
            ("diabetes", "Diabetes"),
            ("cardiovasculares", "Doenças cardiovasculares"),
            ("neoplasias", "Neoplasias"),
            ("alergias", "Alergias"),
            ("outros", "Outros"),
        ), detalhe="Outros (quais?)"),
    )),
    Secao("odontologica", "Histórico odontológico", (
        Item("odonto_queixa",
             "Qual sua queixa principal ou o motivo pelo qual procurou "
             "tratamento?", TEXTO),
        _sn("odonto_dificuldade_mastigar",
            "Tem dificuldade na mastigação de alimentos?"),
        _sn("odonto_dente_sensivel", "Tem algum dente sensível?"),
        _sn("odonto_gengiva_sangra", "Sua gengiva sangra com facilidade?"),
        _sn("odonto_ferida_demora",
            "Já teve ferida nos lábios ou na língua que demorou a melhorar?"),
        _sn("odonto_dificuldade_abrir_boca",
            "Tem dificuldade em abrir a boca?"),
        _sn("odonto_rosto_cansado_manha",
            "Sente o rosto cansado ou dolorido pela manhã (ao acordar)?"),
        _sn("odonto_estalos", "Sente estalos quando mastiga?"),
        Item("odonto_ultima_visita",
             "Quando foi a última vez que esteve no dentista?", TEXTO),
    )),
    Secao("higiene", "Hábitos de higiene bucal", (
        Item("hig_vezes_dia", "Quantas vezes por dia escova os dentes?",
             ESCOLHA, (
                 ("1", "Uma"), ("2", "Duas"), ("3", "Três"),
                 ("4+", "Mais vezes ao dia"),
             )),
        Item("hig_horario", "Qual horário de escovação?", ESCOLHA, (
            ("apos_primeira_refeicao", "Só após a primeira refeição"),
            ("acordar_dormir", "Ao acordar e antes de dormir"),
            ("acordar_refeicoes_dormir",
             "Ao acordar, após as refeições e antes de dormir"),
        )),
        Item("hig_produtos", "O que usa para a higiene bucal?", MULTIPLA, (
            ("escova", "Escova"),
            ("fio_dental", "Fio dental"),
            ("creme_dental", "Creme dental"),
            ("enxaguatorio", "Enxaguatório bucal"),
            ("outro", "Outro"),
        ), detalhe="Outro (qual?)"),
        _sn("hig_fluor_ano", "Usou flúor no último ano?"),
    )),
    Secao("alimentares", "Hábitos alimentares", (
        Item("ali_entre_refeicoes", "Costuma comer entre as refeições?",
             ESCOLHA, SIM_NAO_AS_VEZES),
        Item("ali_dieta_rica", "Dieta rica em:", MULTIPLA, (
            ("acucares", "Açúcares"),
            ("gorduras", "Gorduras"),
            ("carboidratos", "Carboidratos"),
            ("vegetais", "Vegetais e legumes"),
            ("proteinas", "Proteínas"),
        )),
        Item("ali_acucar_manha",
             "Horários da MANHÃ em que costuma ingerir alimentos/bebidas "
             "contendo açúcar fermentável:", MULTIPLA, HORAS),
        Item("ali_acucar_tarde",
             "Horários da TARDE/NOITE em que costuma ingerir alimentos/"
             "bebidas contendo açúcar fermentável:", MULTIPLA, HORAS),
    )),
)

TODOS_OS_ITENS = tuple(item for secao in SECOES for item in secao.itens)
ITENS_POR_CODIGO = {item.codigo: item for item in TODOS_OS_ITENS}

# Garantia contra código duplicado (o que sobrescreveria respostas).
assert len(ITENS_POR_CODIGO) == len(TODOS_OS_ITENS), "código de pergunta repetido"


def rotulo_da_opcao(item, valor):
    return dict(item.opcoes).get(valor, valor)


def montar_resumo(respostas):
    """
    Estrutura pronta para a tela de leitura: por seção, cada pergunta com a
    resposta já traduzida em texto.
    """
    respostas = respostas or {}
    secoes = []
    total = respondidas = 0

    for secao in SECOES:
        linhas = []
        for item in secao.itens:
            valor = respostas.get(item.codigo)
            detalhe = respostas.get(item.codigo_detalhe, "")
            if item.tipo == MULTIPLA:
                valor = [v for v in (valor or []) if v in dict(item.opcoes)]
                texto = ", ".join(rotulo_da_opcao(item, v) for v in valor)
                marcado = bool(valor)
            elif item.tipo == TEXTO:
                texto = valor or ""
                marcado = bool(texto)
            else:
                texto = rotulo_da_opcao(item, valor) if valor else ""
                marcado = bool(valor)

            total += 1
            respondidas += marcado
            linhas.append({
                "item": item,
                "valor": valor,
                "texto": texto,
                "detalhe": detalhe,
                "respondida": marcado,
            })
        secoes.append({"secao": secao, "linhas": linhas})

    return {"secoes": secoes, "total": total, "respondidas": respondidas}