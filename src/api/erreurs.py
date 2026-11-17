"""Erreurs de validation renvoyées en français, champ par champ."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Message français de chaque type d'erreur de Pydantic rencontré par le schéma.
MESSAGES: dict[str, str] = {
    "missing": "Champ obligatoire.",
    "extra_forbidden": "Champ inconnu.",
    "int_type": "Un nombre entier est attendu.",
    "int_parsing": "Un nombre entier est attendu.",
    "int_from_float": "Un nombre entier est attendu.",
    "greater_than": "La valeur doit être supérieure à {gt}.",
    "greater_than_equal": "La valeur doit être supérieure ou égale à {ge}.",
    "less_than_equal": "La valeur doit être inférieure ou égale à {le}.",
    "literal_error": "Valeur non autorisée. Valeurs possibles : {expected}.",
    "value_error": "{error}",
}


def traduire(erreur: dict) -> dict[str, str]:
    """Traduit une erreur de Pydantic en un champ et un message français.

    Args:
        erreur: Erreur décrite par Pydantic : type, emplacement, message, contexte.

    Returns:
        Le champ refusé et la raison. Un type d'erreur non prévu garde le message
        d'origine.
    """
    modele = MESSAGES.get(erreur["type"])
    contexte = {
        cle: str(valeur).replace(" or ", " ou ")
        for cle, valeur in erreur.get("ctx", {}).items()
    }
    message = modele.format(**contexte) if modele else erreur["msg"]
    # Le premier élément de l'emplacement vaut toujours « body ».
    champ = ".".join(str(element) for element in erreur["loc"][1:])
    return {"champ": champ or "corps de la requête", "message": message}


def refuser_donnees_invalides(
    requete: Request, erreur: RequestValidationError
) -> JSONResponse:
    """Répond 422 avec la liste des champs refusés.

    Args:
        requete: Requête reçue, non utilisée.
        erreur: Erreurs relevées par Pydantic sur le corps de la requête.

    Returns:
        La réponse 422, au format du schéma ErreursValidation.
    """
    details = [traduire(detail) for detail in erreur.errors()]
    return JSONResponse(status_code=422, content={"detail": details})
