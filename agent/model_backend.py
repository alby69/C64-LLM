import os
import torch

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


class ModelBackend:
    def __init__(self, model, tokenizer, base_model=None):
        self.model = model
        self.tokenizer = tokenizer
        self.device = model.device if hasattr(model, "device") else "cpu"
        self._base_model = base_model or model
        self._lora_path = None

    def load_lora(self, lora_path):
        from peft import PeftModel

        if self._lora_path == lora_path:
            return True
        self.unload_lora()
        try:
            self.model = PeftModel.from_pretrained(self._base_model, lora_path)
            self._lora_path = lora_path
            print(f"LoRA caricato: {lora_path}")
            return True
        except Exception as e:
            print(f"Errore caricamento LoRA: {e}")
            self.model = self._base_model
            self._lora_path = None
            return False

    def unload_lora(self):
        if self._lora_path:
            self.model = self._base_model
            self._lora_path = None
            print("LoRA rimosso, modello base ripristinato")
        return True

    def generate(self, prompt, max_new_tokens=512, temperature=0.3, top_p=0.9):
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        return self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1] :], skip_special_tokens=True
        )


class LlamaCppBackend:
    """Integrazione llama.cpp per GGUF su CPU."""

    def __init__(self, model_path):
        self.model_path = model_path
        if Llama and model_path and os.path.exists(model_path):
            print(f"Initializing Llama-cpp with {model_path}")
            self.llm = Llama(
                model_path=model_path,
                n_ctx=16384,
                n_threads=os.cpu_count(),
                verbose=False,
            )
        else:
            print(
                "Llama-cpp-python not installed or model path invalid. Using Mock mode."
            )
            self.llm = None

    def load_lora(self, lora_path):
        print("GGUF backend non supporta LoRA dinamico.")
        return False

    def unload_lora(self):
        return True

    def generate(self, prompt, max_new_tokens=512, temperature=0.3, top_p=0.9):
        if self.llm:
            output = self.llm(
                prompt,
                max_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=["<|im_end|>", "<|endoftext|>"],
            )
            return output["choices"][0]["text"]

        return "ERROR: Llama-cpp backend not properly initialized. This is a mock response."


class NanoGPTBackend:
    """Integrazione per l'inferenza di modelli addestrati o fine-tunati con nanoGPT."""

    def __init__(self, model_path, tokenizer_name="gpt2"):
        self.model_path = model_path
        self.tokenizer_name = tokenizer_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None

        print(f"Inizializzazione NanoGPTBackend con {model_path}")

        # Carica il tokenizer di default (GPT-2)
        try:
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        except Exception as e:
            print(f"Errore caricamento tokenizer: {e}")

        # Tenta di caricare il modello nanoGPT
        if model_path and os.path.exists(model_path):
            try:
                import sys
                from pathlib import Path
                nanogpt_path = Path("external/nanoGPT").resolve()
                if str(nanogpt_path) not in sys.path:
                    sys.path.append(str(nanogpt_path))

                from model import GPT, GPTConfig

                print(f"Caricamento checkpoint nanoGPT: {model_path}")
                checkpoint = torch.load(model_path, map_location=self.device)
                gptconf = GPTConfig(**checkpoint['model_args'])
                self.model = GPT(gptconf)

                # Rimuove prefissi indesiderati dallo state dict se necessario
                state_dict = checkpoint['model']
                unwanted_prefix = '_orig_mod.'
                for k, v in list(state_dict.items()):
                    if k.startswith(unwanted_prefix):
                        state_dict[k[len(unwanted_prefix):]] = state_dict.pop(k)

                self.model.load_state_dict(state_dict)
                self.model.to(self.device)
                self.model.eval()
                print("Modello nanoGPT caricato con successo.")
            except Exception as e:
                print(f"Caricamento nanoGPT fallito/non ancora addestrato: {e}. Uso in modalita di fallback.")
        else:
            print(f"Percorso modello nanoGPT non valido o assente: {model_path}. Uso in modalita di fallback.")

    def load_lora(self, lora_path):
        print("Il backend nanoGPT non supporta LoRA dinamico.")
        return False

    def unload_lora(self):
        return True

    def generate(self, prompt, max_new_tokens=512, temperature=0.3, top_p=0.9):
        if self.model and self.tokenizer:
            try:
                # Tokenizzazione del prompt
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
                idx = inputs["input_ids"]

                # Generazione dei token usando il modello nanoGPT
                # Il modello di Karpathy implementa .generate(idx, max_new_tokens, temperature, top_k)
                # Adattiamo i parametri della chiamata
                top_k = int(top_p * 100) if top_p else None
                with torch.no_grad():
                    outputs = self.model.generate(
                        idx,
                        max_new_tokens,
                        temperature=temperature if temperature > 0 else 1.0,
                        top_k=top_k
                    )

                # Decodifica della risposta generata (escludendo il prompt iniziale)
                generated_tokens = outputs[0][idx.shape[1]:]
                return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            except Exception as e:
                return f"Errore durante la generazione con nanoGPT: {e}. Fallback: Risposta simulata per prompt '{prompt[:30]}...'"

        # Fallback se il modello non e' fisicamente caricato (es. durante i test o prima del training reale)
        return (
            f"Questo e' un feedback simulato dal backend nanoGPT (modello fisico non presente in {self.model_path}).\n"
            f"Prompt ricevuto: {prompt[:100]}..."
        )
