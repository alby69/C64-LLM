import gradio as gr
from utils.acme_linter import ACMELinter

class RetroCodeEditor:
    """
    Rappresenta un editor di codice retro con tema Commodore 64, syntax highlighting
    e integrazione linter asincrona.
    """
    def __init__(self):
        self.linter = ACMELinter()

    def get_c64_css(self):
        """Restituisce le regole CSS retro per l'interfaccia C64."""
        return """
        .c64-retro-editor {
            background-color: #3b3b98 !important;
            color: #00d2ff !important;
            font-family: 'Courier New', Courier, monospace !important;
            border: 8px solid #5a5ad6 !important;
            padding: 10px;
            border-radius: 4px;
        }
        .c64-retro-editor textarea {
            background-color: #3b3b98 !important;
            color: #a3e5ff !important;
            font-family: 'Courier New', Courier, monospace !important;
            border: none !important;
        }
        .c64-btn {
            background-color: #5a5ad6 !important;
            color: #fff !important;
            border: 2px solid #00d2ff !important;
            font-family: 'Courier New', Courier, monospace !important;
            font-weight: bold;
        }
        .c64-btn:hover {
            background-color: #00d2ff !important;
            color: #3b3b98 !important;
        }
        """

    def render_monaco_html(self, initial_code=""):
        """Genera il codice HTML per incorporare Monaco Editor nella UI Gradio."""
        escaped_code = initial_code.replace("`", "\\`").replace("$", "\\$")

        return f"""
        <div style="border: 4px solid #5a5ad6; border-radius: 6px; overflow: hidden; background-color: #1e1e1e;">
            <div style="background-color: #3b3b98; color: #00d2ff; padding: 6px 12px; font-family: monospace; font-weight: bold; display: flex; justify-content: space-between;">
                <span>C64 RETRO ASSEMBLER EDITOR v2.0</span>
                <span>MONACO POWERED</span>
            </div>
            <div id="monaco-container" style="height: 400px; width: 100%;"></div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js"></script>
        <script>
            require.config({{ paths: {{ vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.39.0/min/vs' }} }});
            require(['vs/editor/editor.main'], function() {{
                // Definisci un tema personalizzato C64 Retro
                monaco.editor.defineTheme('c64-retro-theme', {{
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        {{ token: 'comment', foreground: '7a7ad6', fontStyle: 'italic' }},
                        {{ token: 'keyword', foreground: '00d2ff', fontStyle: 'bold' }},
                        {{ token: 'number', foreground: 'ffcc00' }},
                        {{ token: 'string', foreground: '00ffcc' }},
                    ],
                    colors: {{
                        'editor.background': '#3b3b98',
                        'editor.foreground': '#a3e5ff',
                        'editor.lineHighlightBackground': '#4e4eb2',
                        'editorCursor.foreground': '#00d2ff',
                        'editor.selectionBackground': '#5a5ad6',
                        'editorLineNumber.foreground': '#7a7ad6',
                    }}
                }});

                window.editor = monaco.editor.create(document.getElementById('monaco-container'), {{
                    value: `{escaped_code}`,
                    language: 'ini', // Fallback syntax highlighting
                    theme: 'c64-retro-theme',
                    fontSize: 14,
                    fontFamily: 'Courier New, monospace',
                    minimap: {{ enabled: false }},
                    automaticLayout: true
                }});

                // Invia modifiche a Gradio quando l'editor cambia
                window.editor.onDidChangeModelContent(function() {{
                    const val = window.editor.getValue();
                    // Trova l'elemento textbox nascosto di Gradio per sincronizzare il codice
                    const gradioTextarea = window.parent.document.querySelector('.c64-sync-target textarea');
                    if (gradioTextarea) {{
                        gradioTextarea.value = val;
                        gradioTextarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }});

                // Ascolta eventi postMessage da altri tab (es: Galleria Asset)
                window.addEventListener('message', function(event) {{
                    if (event.data && event.data.type === 'select_asset') {{
                        const idInput = window.parent.document.querySelector('.c64-selected-asset input');
                        if (idInput) {{
                            idInput.value = event.data.id;
                            idInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            idInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                }});
            }});
        </script>
        """

    def lint_code(self, code):
        """Interfaccia del linter per Gradio."""
        errors = self.linter.lint(code)
        if not errors:
            return "✅ Nessun errore sintattico rilevato. Il codice è pronto per la compilazione."

        lines = []
        for err in errors:
            sev = "🛑 ERRORE" if err["severity"] == "error" else "⚠️ WARNING"
            lines.append(f"Linea {err['line']}: {sev} - {err['message']}\n   Codice: {err['text']}")

        return "\n".join(lines)
