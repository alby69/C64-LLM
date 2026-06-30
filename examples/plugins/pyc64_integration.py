"""
Esempio di plugin in stile Cheshire Cat per integrare PYC64 come Tools
all'interno dell'ecosistema C64 Intelligence.
"""

# Supponiamo che PYC64 abbia una funzione per creare file D64
try:
    from tools.pyc64.disk import create_d64_from_prg
except ImportError:
    # Mock per dimostrazione
    def create_d64_from_prg(prg_path, d64_path):
        return f"D64 creato in {d64_path} con {prg_path}"

def tool(func):
    """Decorator simulato per marcare le funzioni come Tools per l'LLM"""
    func._is_tool = True
    return func

@tool
def build_c64_disk(prg_filename: str, disk_name: str):
    """
    Crea un'immagine disco D64 a partire da un file PRG compilato.
    Utile per raggruppare i file per l'emulatore.
    """
    output_path = f"data/output/{disk_name}.d64"
    source_path = f"data/output/{prg_filename}"

    result = create_d64_from_prg(source_path, output_path)
    return f"Operazione completata tramite PYC64: {result}"

@tool
def analyze_memory_usage(asm_file: str):
    """
    Analizza un file assembly e restituisce una mappa della memoria
    usando le utility di PYC64.
    """
    # Esempio di integrazione con logica PYC64
    return "Analisi memoria completata: $C000-$C1FF occupati."

def hook_agent_prompt_prefix(prefix, context):
    """
    Hook per iniettare contesto dai Tutorial nel prompt di sistema.
    """
    if "game" in context.get("task_type", ""):
        prefix += "\nUsa le convenzioni di naming di C64GameTutorial (es. prefix 'ENT_' per entità)."
    return prefix
