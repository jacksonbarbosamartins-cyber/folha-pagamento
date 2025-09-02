
import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Folha de Pagamento 2025 – Multi Funcionários", layout="wide")

# ---------------- Parâmetros ---------------- #
HORAS_MENSAL = 220  # base comum de cálculo

# ---------------- Funções de Cálculo ---------------- #
def calcular_inss_detalhado(salario):
    """
    Tabela 2025 (exemplo) com parcela a deduzir.
    Retorna dict com valor, aliquota, deducao, faixa_limite.
    """
    faixas = [
        (1518.00, 0.075, 0.00),
        (2793.88, 0.09, 22.77),
        (4190.83, 0.12, 106.59),
        (8157.41, 0.14, 190.40),
    ]
    teto = 908.85
    for limite, aliquota, deducao in faixas:
        if salario <= limite:
            valor = max(salario * aliquota - deducao, 0.0)
            return {
                "valor": min(valor, teto),
                "aliquota": aliquota,
                "deducao": deducao,
                "faixa_limite": limite
            }
    return {
        "valor": teto,
        "aliquota": 0.14,
        "deducao": 190.40,
        "faixa_limite": 8157.41
    }

def calcular_irrf_detalhado(base, dependentes=0, desconto_simplificado=False):
    """
    Tabela 2025 com parcela a deduzir.
    Se usar desconto simplificado, subtrai R$ 607,20 da base;
    caso contrário, aplica dedução por dependentes de R$ 189,59/cada.
    """
    deducao_dependentes = dependentes * 189.59
    if desconto_simplificado:
        base_calculo = base - 607.20
        desc_txt = "Desconto simplificado R$ 607,20"
    else:
        base_calculo = base - deducao_dependentes
        desc_txt = f"Deduções por dependentes: R$ {deducao_dependentes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if base_calculo <= 0:
        return {"valor": 0.0, "aliquota": 0.0, "deducao": 0.0, "faixa_limite": 0.0, "base_calculo": base_calculo, "descricao": desc_txt}

    faixas = [
        (2428.80, 0.0, 0.0),
        (2826.65, 0.075, 182.16),
        (3751.05, 0.15, 394.16),
        (4664.68, 0.225, 675.49),
        (9999999, 0.275, 908.73),
    ]

    for limite, aliquota, deducao in faixas:
        if base_calculo <= limite:
            valor = max(base_calculo * aliquota - deducao, 0.0)
            return {
                "valor": valor,
                "aliquota": aliquota,
                "deducao": deducao,
                "faixa_limite": limite,
                "base_calculo": base_calculo,
                "descricao": desc_txt
            }
    return {
        "valor": 0.0, "aliquota": 0.0, "deducao": 0.0, "faixa_limite": 0.0, "base_calculo": base_calculo, "descricao": desc_txt
    }

def calcular_itens_salariais(salario, he_horas, he_percent, noturno_horas, noturno_percent):
    """
    he_percent e noturno_percent devem ser informados em percentuais (ex.: 50 para 50%).
    - Hora extra: paga a hora normal + adicional. Valor = horas * (salario/220) * (1 + he%)
    - Adicional noturno: adicional sobre hora normal. Valor = horas * (salario/220) * (noturno%)
    """
    valor_hora = salario / HORAS_MENSAL if HORAS_MENSAL else 0.0
    he_valor = he_horas * valor_hora * (1.0 + he_percent/100.0)
    noturno_valor = noturno_horas * valor_hora * (noturno_percent/100.0)
    return valor_hora, he_valor, noturno_valor

def format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_pdf(func):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w/2, h - 40, "Holerite – Folha de Pagamento 2025")

    y = h - 80
    c.setFont("Helvetica", 11)
    lines = [
        f"Funcionário: {func['nome']}",
        f"Salário Base: {format_brl(func['salario'])}",
        f"Horas Extras: {func['he_horas']}h a {func['he_percent']}% → {format_brl(func['he_valor'])}",
        f"Adicional Noturno: {func['noturno_horas']}h a {func['noturno_percent']}% → {format_brl(func['noturno_valor'])}",
        f"Benefícios: {format_brl(func['beneficios'])}",
        f"Vale: {format_brl(func['vale'])}",
        f"Outros Descontos: {format_brl(func['descontos'])}",
        f"—",
        f"INSS: {format_brl(func['inss_val'])} (alíquota {func['inss_aliq']*100:.1f}%, dedução {format_brl(func['inss_ded'])}, faixa até {format_brl(func['inss_limite'])})",
        f"Base IRRF: {format_brl(func['ir_base'])}",
        f"IRRF: {format_brl(func['ir_val'])} (alíquota {func['ir_aliq']*100:.1f}%, dedução {format_brl(func['ir_ded'])}, faixa até {format_brl(func['ir_limite'])})",
        f"—",
        f"Salário Líquido: {format_brl(func['liquido'])}",
    ]

    for line in lines:
        c.drawString(60, y, line)
        y -= 20
        if y < 80:
            c.showPage()
            y = h - 60
            c.setFont("Helvetica", 11)

    c.setFont("Helvetica", 10)
    c.drawString(60, 60, "Assinatura: __________________________________")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf

# ---------------- Estado ---------------- #
if "funcionarios" not in st.session_state:
    st.session_state.funcionarios = []

st.title("Folha de Pagamento 2025 – Multi Funcionários")

with st.sidebar:
    st.header("Cadastrar Funcionário")
    nome = st.text_input("Nome do funcionário")
    salario = st.number_input("Salário bruto (R$)", min_value=0.0, value=5000.0, step=100.0)
    dependentes = st.number_input("Dependentes", min_value=0, value=0, step=1)
    # Adicionais
    he_horas = st.number_input("Horas extras (quantidade)", min_value=0.0, value=0.0, step=1.0)
    he_percent = st.number_input("Percentual HE (%)", min_value=0.0, value=50.0, step=5.0)
    noturno_horas = st.number_input("Adicional noturno (horas)", min_value=0.0, value=0.0, step=1.0)
    noturno_percent = st.number_input("Percentual Noturno (%)", min_value=0.0, value=20.0, step=5.0)
    # Benefícios e descontos
    beneficios = st.number_input("Benefícios (R$)", min_value=0.0, value=0.0, step=50.0)
    vale = st.number_input("Vale-transporte/refeição (R$)", min_value=0.0, value=0.0, step=50.0)
    descontos = st.number_input("Outros descontos (R$)", min_value=0.0, value=0.0, step=50.0)

    usar_desconto_simplificado = st.checkbox("IRRF: usar desconto simplificado (R$ 607,20)?", value=False)

    if st.button("Adicionar funcionário", use_container_width=True):
        if not nome.strip():
            st.warning("Informe o nome do funcionário.")
        else:
            # Cálculos
            valor_hora, he_valor, noturno_valor = calcular_itens_salariais(salario, he_horas, he_percent, noturno_horas, noturno_percent)
            vencimentos = salario + he_valor + noturno_valor + beneficios
            inss_info = calcular_inss_detalhado(vencimentos)
            inss = inss_info["valor"]
            ir_base = vencimentos - inss - vale - descontos
            ir_info = calcular_irrf_detalhado(ir_base, dependentes, usar_desconto_simplificado)
            ir = ir_info["valor"]
            liquido = vencimentos - (inss + ir + vale + descontos)

            func = {
                "nome": nome,
                "salario": salario,
                "valor_hora": valor_hora,
                "he_horas": he_horas,
                "he_percent": he_percent,
                "he_valor": he_valor,
                "noturno_horas": noturno_horas,
                "noturno_percent": noturno_percent,
                "noturno_valor": noturno_valor,
                "beneficios": benefícios if (benefícios := beneficios) else beneficios,  # apenas para garantir variável
                "vale": vale,
                "descontos": descontos,
                "dependentes": dependentes,
                "desconto_simplificado": usar_desconto_simplificado,
                "vencimentos": vencimentos,
                "inss_val": inss,
                "inss_aliq": inss_info["aliquota"],
                "inss_ded": inss_info["deducao"],
                "inss_limite": inss_info["faixa_limite"],
                "ir_base": ir_info.get("base_calculo", 0.0),
                "ir_val": ir,
                "ir_aliq": ir_info["aliquota"],
                "ir_ded": ir_info["deducao"],
                "ir_limite": ir_info["faixa_limite"],
                "liquido": liquido
            }
            st.session_state.funcionarios.append(func)
            st.success(f"Funcionário '{nome}' adicionado!")

# ---------------- Listagem ---------------- #
st.subheader("📋 Funcionários cadastrados")

if len(st.session_state.funcionarios) == 0:
    st.info("Nenhum funcionário cadastrado ainda.")
else:
    # Tabela resumida
    df = pd.DataFrame([{
        "Funcionário": f["nome"],
        "Vencimentos": format_brl(f["vencimentos"]),
        "INSS": format_brl(f["inss_val"]),
        "IRRF": format_brl(f["ir_val"]),
        "Vale/Outros": format_brl(f["vale"] + f["descontos"]),
        "Líquido": format_brl(f["liquido"]),
    } for f in st.session_state.funcionarios])
    st.dataframe(df, use_container_width=True)

    # Exportar CSV
    df_export = pd.DataFrame(st.session_state.funcionarios)
    csv = df_export.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Exportar lista (CSV)", csv, "funcionarios.csv", "text/csv")

    st.markdown("---")
    # Cartões detalhados
    for idx, f in enumerate(st.session_state.funcionarios):
        with st.expander(f"🧾 {f['nome']} — Holerite e detalhes", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Vencimentos", format_brl(f["vencimentos"]))
            c2.metric("INSS", format_brl(f["inss_val"]))
            c3.metric("IRRF", format_brl(f["ir_val"]))
            c4.metric("Líquido", format_brl(f["liquido"]))

            st.write("**Base**")
            st.write(f"- Salário base: {format_brl(f['salario'])} | Valor hora: {format_brl(f['valor_hora'])}")
            st.write(f"- HE: {f['he_horas']}h a {f['he_percent']}% → {format_brl(f['he_valor'])}")
            st.write(f"- Adic. Noturno: {f['noturno_horas']}h a {f['noturno_percent']}% → {format_brl(f['noturno_valor'])}")
            st.write(f"- Benefícios: {format_brl(f['beneficios'])}")
            st.write(f"- Vencimentos: {format_brl(f['vencimentos'])}")

            st.write("**Descontos**")
            st.write(f"- INSS: {format_brl(f['inss_val'])} (alíquota {f['inss_aliq']*100:.1f}%, dedução {format_brl(f['inss_ded'])}, faixa até {format_brl(f['inss_limite'])})")
            ir_desc = "Desconto simplificado R$ 607,20" if f["desconto_simplificado"] else f"Deduções por dependentes (R$ 189,59 x {f['dependentes']})"
            st.write(f"- IRRF: {format_brl(f['ir_val'])} (alíquota {f['ir_aliq']*100:.1f}%, dedução {format_brl(f['ir_ded'])}, faixa até {format_brl(f['ir_limite'])} | {ir_desc}; Base IR: {format_brl(f['ir_base'])})")
            st.write(f"- Vale: {format_brl(f['vale'])}")
            st.write(f"- Outros descontos: {format_brl(f['descontos'])}")

            pdf_buf = gerar_pdf(f)
            st.download_button("📥 Baixar Holerite (PDF)", pdf_buf, f"holerite_{idx+1}_{f['nome'].replace(' ', '_')}.pdf", "application/pdf", key=f"pdf_{idx}")
