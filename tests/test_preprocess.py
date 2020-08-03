from autocom.preprocess import clean_text


def test_clean_text():
    text = """
    AMMIANI MARCELLINI HISTORIAE LIBER XIV
    1 2 3 4 5 6 7 8 9 10 11
    
    Galli Caesaris saevitia.
    
    [1] 1 Post emensos insuperabilis expeditionis eventus languentibus partium animis.
    """
    output = clean_text(text)
    correct = "ammiani marcellini historiae liber xiv galli caesaris saevitia post emensos insuperabilis " \
              "expeditionis eventus languentibus partium animis"
    assert output == correct
