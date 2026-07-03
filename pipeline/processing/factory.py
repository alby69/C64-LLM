import os

class ExtractorFactory:
    @staticmethod
    def get_extractor(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".pdf":
            from pipeline.processing.pdf2marker import convert_pdf
            return convert_pdf
        elif ext == ".d64":
            from packages.c64extractor.extract_d64 import extract_d64
            # Wrapping to match a common interface if needed,
            # but for now just returning the function
            return extract_d64
        elif ext == ".prg":
            from packages.c64extractor.extract_prg import extract_prg
            return extract_prg
        elif ext == ".g64":
            from packages.c64extractor.extract_g64 import extract_g64
            return extract_g64
        return None
