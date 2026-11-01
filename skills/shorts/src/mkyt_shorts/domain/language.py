"""Datos por idioma que usan la selección de finales y de ganchos. Idioma desconocido: se usa la unión de los conocidos."""

# Palabras que no pueden ser la última de una frase completa (el habla sigue después de ellas)
NO_CIERRAN = {
    "es": {
        "y", "o", "u", "e", "que", "de", "del", "a", "al", "en", "con", "por", "para", "sin", "sobre", "entre", "pero",
        "porque", "pues", "como", "si", "ni", "el", "la", "los", "las", "un", "una", "unos", "unas", "lo", "le", "les",
        "se", "me", "te", "su", "sus", "mi", "es", "ha", "han", "fue", "son", "era", "digamos", "sea", "cuando", "donde",
        "mas", "muy", "ya", "tambien", "tan", "tanto", "tiene", "tienen", "hay", "va", "van", "creo", "bueno", "entonces",
        "esto", "eso", "este", "esta", "esos", "esas", "cada", "otro", "otra", "mismo", "siempre", "solo", "sino", "aunque",
    },
    "en": {
        "and", "or", "but", "so", "because", "if", "when", "while", "that", "which", "who", "the", "a", "an", "of", "to",
        "in", "on", "at", "for", "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "can", "could", "should", "my", "your", "his", "her", "its", "our",
        "their", "this", "these", "those", "than", "then", "just", "very", "really", "like", "about", "into", "not",
    },
}

# Conectores con los que no debe empezar un clip ni un gancho
CONECTORES_INICIO = {
    "es": {"y", "o", "pero", "que", "porque", "pues", "entonces", "sino", "aunque", "bueno", "sea", "digamos", "es", "si"},
    "en": {"and", "or", "but", "so", "because", "then", "well", "like", "also", "which", "that"},
}


def _union(table, lang):
    if lang in table:
        return set(table[lang])
    out = set()
    for v in table.values():
        out |= v
    return out


def no_cierran(lang):
    return _union(NO_CIERRAN, lang)


def conectores_inicio(lang):
    return _union(CONECTORES_INICIO, lang)
