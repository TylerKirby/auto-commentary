from autocom.vocab import generate_vocab_list


def test_generate_vocab_list():
    text = "ammiani marcellini historiae liber xiv galli caesaris saevitia post emensos insuperabilis expeditionis " \
           "eventus languentibus partium animis"
    output = generate_vocab_list(text)
    correct = ""
