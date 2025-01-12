import micropip
await micropip.install(
    'https://files.pythonhosted.org/packages/e0/02/c10a69ff21d6679a6b6e28c42cd265bec2cdd9be3dcbbee830a10fa4b0e5/pyhfst-1.3.0-py2.py3-none-any.whl'
    #'https://files.pythonhosted.org/packages/eb/f5/3ea71e974dd0117b95a54ab2c79d781b4376d257d91e4c2249605f4a54ae/pyhfst-1.3.0-py2.py3-none-any.whl'
    #'https://files.pythonhosted.org/packages/eb/f5/3ea71e974dd0117b95a54ab2c79d781b4376d257d91e4c2249605f4a54ae/pyhfst-1.2.0-py2.py3-none-any.whl'
    #'./pyhfst-1.2.0-py2.py3-none-any.whl'
)
await micropip.install(
    'https://files.pythonhosted.org/packages/40/44/4a5f08c96eb108af5cb50b41f76142f0afa346dfa99d5296fe7202a11854/tabulate-0.9.0-py3-none-any.whl'
)
from pyweb import pydom
import pyscript
import asyncio
from js import console, Uint8Array, File, URL, document, window #File et seq were added for download, maybe pyscript.File, URL, document will work?
import io #this was added for download
from pyodide.ffi.wrappers import add_event_listener
import regex
import pyhfst
import tabulate
#print("Coming soon: put in a Nishnaabemwin text, get back a (rough) interlinear analysis of the text")
#print("For now, a demonstration that a functioning analyzer is loaded")

###functions copied directly/modified from elsewhere in the repo
def parse_pyhfst(transducer, *strings):
    h = {}
    parser = pyhfst.HfstInputStream(transducer).read()
    for s in strings: 
        if s not in h: 
            h[s] = []
            p = parser.lookup(s)
            if not p: h[s].append((s+"+?", 0.00))
            else: 
                for q in p: h[s].append((regex.sub("@.*?@", "" ,q[0]), q[1])) #filtering out flag diacritics, which the hfst api does not do as of dec 2023
    return h

def sep_punct(string, drop_punct): #diy tokenization, use nltk?
    if not drop_punct: return "'".join(regex.sub("(\"|“|\(|\)|”|…|:|;|,|\*|\.|\?|!|/)", " \g<1> ", string).split("’")) #separate all punc, then replace single quote ’ with '
    return "'".join(regex.sub("(\"|“|\(|\)|”|…|:|;|,|\*|\.|\?|!|/)", " ", string).split("’")) #remove all punc, then replace single quote ’ with '

def min_morphs(*msds):
    """the length of the shortest morphosyntactic description"""
    return min([m[0].count("+") for m in msds])

def disambiguate(target, f, *msds): 
    """the earliest of the morphosyntactic descriptions|f(m) = target"""
    #prioritizing order allows weighting schemes to be exploited
    for i in range(len(msds)):
        if f(msds[i]) == target: return i
    #first default
    return 0

def parse_text(drop_punct, *sentences):
    analysis = []
    analyses = parse_pyhfst("./morphophonologyclitics_analyze.hfstol", *[x for s in sentences for x in sep_punct(s.lower(), drop_punct).split()])
    for s in sentences:
        a = []
        for w in sep_punct(s.lower(), drop_punct).split():
            best = analyses[w][disambiguate(min_morphs(*analyses[w]), min_morphs, *analyses[w])][0]
            console.log(best)
            a.append(best)
        analysis.append(a)
    return analysis

def pad(*lists_of_strings):
    #lists must be same length!
    nu_lists = []
    padlen = []
    for i in range(len(lists_of_strings)):
        nu = []
        for j in range(len(lists_of_strings[i])): #pad items in list to max length at their indices
            if not i: padlen.append(max([len(lists_of_strings[k][j]) for k in range(len(lists_of_strings))]))
            nu.append(lists_of_strings[i][j]+" "*(padlen[j]-len(lists_of_strings[i][j])))
        nu_lists.append(nu)
    return nu_lists

def readin(filename):
    holder = []
    with open(filename, 'r') as f_in:
        for line in f_in:
            holder.append(line.strip())
    return holder

def mk_glossing_dict(*strings):
    gd = {}
    for s in strings:
        chunked = s.split("\t")
        if chunked[0] not in gd: gd[chunked[0]] = chunked[1]
        #else: gd[chunked[0]] = gd[chunked[0]] + " HOMOPHONE DEFINITION>" + chunked[1]
        else: gd[chunked[0]] = gd[chunked[0]] + "/" + chunked[1]
    return gd

def extract_lemma(string, pos_regex):
    """pull lemma out of string"""
    #lemma is always followed by Part Of Speech regex
    #lemma may be preceeded by prefixes, else word initial
    #if regex.search(pos_regex, string): return regex.search("(^|\+)(.*?)"+pos_regex, string).group(2)
    if regex.search(pos_regex, string): return regex.split(pos_regex, string)[0].split("+")[-1] #last item before pos tag, after all other morphemes, is lemma
    return None

def lemmatize(pos_regex, *analysis):
    return [extract_lemma(a, pos_regex) for a in analysis]

def formatted(interpreted):
    out = []
    out.append(interpreted["Head"])
    if interpreted["DerivChain"] != interpreted["Head"]: out.append("("+interpreted["DerivChain"]+")")
    if interpreted["Periph"]: out.append(interpreted["Periph"])
    if interpreted["Head"].startswith("N") and interpreted["S"]["Pers"]: out.append("Pos:"+"".join([interpreted["S"]["Pers"], interpreted["S"]["Num"]]))
    if interpreted["S"]["Pers"] and not interpreted["Head"].startswith("N"): out.append("S:"+"".join([interpreted["S"]["Pers"], interpreted["S"]["Num"]]))
    if interpreted["O"]["Pers"]: out.append("O:"+"".join([interpreted["O"]["Pers"], interpreted["O"]["Num"]]))
    if interpreted["Order"]: out.append(interpreted["Order"])
    if interpreted["Neg"]: out.append(interpreted["Neg"])
    if interpreted["Mode"]: out.append(" ".join(interpreted["Mode"]))
    if any(interpreted["Else"]): out.append(" ".join([x for x in interpreted["Else"] if x]))
    return " ".join(out)


def interpret(analysis_in):
    summary = {"S":{"Pers":"", "Num":""}, "O":{"Pers":"", "Num":""}, "DerivChain":"", "Head":"", "Order":"", "Neg":"", "Mode":[], "Periph":"", "Else": [x for x in analysis_in["preforms"]+analysis_in["clitic"]]}
    inversion = False #if true, S/O will be inverted at end
    summary["S"]["Pers"] = analysis_in["prefix"][0]
    summary["DerivChain"] = ">".join([x for x in analysis_in["derivation"]])
    summary["Head"] = analysis_in["derivation"][-1]
    if summary["Head"] == "VTI": summary["O"]["Pers"] = "0" #cheating a little and not putting this in the theme sign info because we don't actually have a suffix tag for VTI themes
    if summary["Head"] == "VAIO": 
        summary["O"]["Pers"] = "3" #cheating a little and not putting this in the theme sign info because VAIOs don't actually have themes
        if analysis_in["suffixes"][-1] == "3": analysis_in["suffixes"].pop() #in some VAIO forms there is a real third person object morpheme, but it is redundant, so dropping it
    while analysis_in["suffixes"]:
        #gnarly list of elif statements
        #general strategy: fill object information with theme sign, then fill object number information, then unify prefix information with number information in subject field, then fill in subject information with remaining suffixes 
        s = analysis_in["suffixes"].pop(0)
        if s == "Neg": summary["Neg"] = s
        elif s == "Prt": summary["Mode"].append(s)
        elif s == "Dub": summary["Mode"].append(s)
        elif s == "Voc": summary["Mode"].append(s)
        elif s == "Cnj": summary["Order"] = s
        elif s == "Imp": 
            summary["Order"] = s
            if summary["Head"] == "VTA": #VTA imperative object information is not in a theme sign, but directly spelled out in tags that are not always immediately adjacent to order tag, so here's a hack that goes backwards through the tags and updates subject and object information while removing the argument information from the computation
                h = []
                subject = True
                while "3" in analysis_in["suffixes"] or "2" in analysis_in["suffixes"] or "1" in analysis_in["suffixes"]:
                    h.append(analysis_in["suffixes"].pop())
                    if "3" in h or "2" in h or ("1" in h and analysis_in["suffixes"][-1:] != ["2"]):
                        if subject: 
                            summary["S"]["Pers"] = h[0]
                            summary["S"]["Num"] = "".join(h[1:])
                            h = []
                            subject = False
                        else:
                            summary["O"]["Pers"] = h[0]
                            summary["O"]["Num"] = "".join(h[1:])
        #{extracting theme sign (primarily object person) information 
        #IND        CNJ
        #Thm1       Thm1
        #Thm1Pl2    Thm1Pl2
        #Thm2       Thm2a
        #           Thm2b
        #ThmDir     ThmDir #3|3pl -> 3(pl) v 3', NEG ONLY:  #1|1pl      3|3pl   -> 1(pl)    v 3(pl), 
                                                            #2|21pl|2pl 3|3pl   -> 2(1(pl)) v 3(pl)
        #           ThmNul #                     POS ONLY:  #1|1pl      3|3pl   -> 1(pl)    v 3(pl), 
                                                            #2|21pl|2pl 3|3pl   -> 2(1(pl)) v 3(pl)
        #ThmInv     ThmInv #1|1pl -> 0 v 1(pl), 2|21pl|2pl -> 0 v 2(1(pl)), 3|3pl -> 0/3' v 3(pl) NEG ONLY: 2pl 3 -> 3 v 2pl (Thm2a not present, handled when 2 Pl is filled into prefixless subject information)
        #{local theme signs
        elif (s == "Thm1Pl2" or s == "Thm1" or s == "Thm2"):
            summary["O"]["Pers"] = "1"
            if s == "Thm2" or s == "Thm1Pl2": inversion = True
            if s == "Thm1Pl2": summary["O"]["Num"] = "Pl"
                #summary["S"]["Pers"] = "2" #not needed because in ind there is a prefix and in cnj there is a following +2
        elif (s == "Thm2a" or s == "Thm2b"):
            summary["O"]["Pers"] = "2"
            #summary["S"]["Pers"] = "1" #default, though later 3 may over ride
            #local theme signs end}
        elif (s == "ThmDir" or s == "ThmInv" or s == "ThmNul"):
            summary["O"]["Pers"] = "3"
            if s == "ThmInv": inversion = True
            if summary["Order"] == "Cnj" and s == "ThmInv": summary["O"]["Pers"] = "0" #will need to revise if 3 is encountered later
        #} extracting theme sign information end
        #{getting number information for theme signs/objects, also finding inanimate subjects
        elif summary["O"]["Pers"] == "1" and s == "1" and analysis_in["suffixes"][0:1] == ["Pl"]:  #this should only happen with thm1 (see below)
            #first person objects are only written in with Thm1, Thm2, Thm1Pl2. 
            #Thm2, Thm1Pl2 are never followed by 1pl (bc Thm1Pl2 is how you indicate first person plurals). 
            #Thm1 .* 1Pl precludes 2pl marking, and so is ambiguous for second person number.  1 obj...1pl = 2Pl/2 vs 1pl.  it never means 21pl bc ban on XvX
            analysis_in["suffixes"].pop(0)
            summary["O"]["Num"] = "Pl"
            #summary["S"]["Pers"] = "2" #redundant, but VTA Cnj Thm1 1Pl needs a default value. because 1Pl blocks 2 person marking ... maybe just add that marking in the model?, no because there are later markings that can appear
            summary["S"]["Num"] = "Pl/2"
        elif summary["O"]["Pers"] == "2" and s == "2" and analysis_in["suffixes"][0:2] == ["1", "Pl"]:
            analysis_in["suffixes"].pop(0)
            analysis_in["suffixes"].pop(0)
            summary["O"]["Num"] = "1Pl"
        elif summary["O"]["Pers"] == "2" and s == "2" and analysis_in["suffixes"][0:1] == ["Pl"]:
            analysis_in["suffixes"].pop(0)
            summary["O"]["Num"] = "Pl"
        elif summary["O"]["Pers"] == "3" and s == "3" and analysis_in["suffixes"][0:1] == ["4"]:
            analysis_in["suffixes"].pop(0)
            summary["O"]["Num"] = "Obv"
        elif summary["O"]["Pers"] == "3" and s == "3" and analysis_in["suffixes"][0:1] == ["Pl"]:
            analysis_in["suffixes"].pop(0)
            summary["O"]["Num"] = "Pl"
        elif summary["O"]["Pers"] == "3" and s == "0": #VTA indep (inverses), have overt suffs for inanimates, need to over ride the default 3 here
            summary["O"]["Pers"] = "0"
            if analysis_in["suffixes"][0:1] == ["Pl"]: #there is a gratuitous +0 suffix in VAIO indeps with singular actors, so it is possible to encounter solitary 0 and 0+Pl. if VTIs had a gratuitous +0 suffix, we would still need next elif, because there would be +0.*+0+Pl strings
                analysis_in["suffixes"].pop(0)
                summary["O"]["Num"] = "Pl"
        elif summary["O"]["Pers"] == "0" and s == "0" and analysis_in["suffixes"][0:1] == ["Pl"]: #there is no longer a gratuitous +0 suffix in VTI indeps with singular actors, so no deliberately clunky syntax needed to drop the +0 tag
            analysis_in["suffixes"].pop(0)
            summary["O"]["Num"] = "Pl"
        #}theme sign number end
        #{getting number information for person values specified by prefix == NOT CONJUNCT!
        elif analysis_in["prefix"][0] == "1" and s == "1" and analysis_in["suffixes"][0:1] == ["Pl"]: 
            summary["S"]["Num"] = "Pl"
            analysis_in["suffixes"].pop(0)
        elif analysis_in["prefix"][0] == "2" and s == "1" and analysis_in["suffixes"][0:1] == ["Pl"]: #this does not mess up VTA local themes, since it is a lower elif (2...Thm1...1Pl = 2Pl/2 v 1pl != 21Pl)
            analysis_in["suffixes"].pop(0)
            summary["S"]["Num"] = "1Pl"
        elif analysis_in["prefix"][0] == "2" and s == "2" and analysis_in["suffixes"][0:1] == ["Pl"]:
            analysis_in["suffixes"].pop(0)
            #if summary["O"]["Pers"] == "1" and summary["S"]["Pers"] == "2" and inversion: summary["S"]["Num"] == "Pl"  ## before inversion (thm1sg/thm1pl .*2pl) = (2pl v 1sg/2pl v 1pl), so no need to specify a special case here 
            #note: there is no further number information in another slot for first persons here ... like theme signs really are object agreement and inversion swoops them into subjecthood (and/or peripheral suffixes are just for 3rd persons)
            summary["S"]["Num"] = "Pl" 
        elif analysis_in["prefix"][0] == "3" and s == "2" and analysis_in["suffixes"][0:1] == ["Pl"]:
            summary["S"]["Num"] = "Pl"
            analysis_in["suffixes"].pop(0)
        #end prefix number obtained}
        #{getting person/number information from suffixes
        elif (not summary["S"]["Pers"]) and s == "1":
            summary["S"]["Pers"] = "1"
            if analysis_in["suffixes"][0:1] == ["Pl"]:
                summary["S"]["Num"] = "Pl"
                analysis_in["suffixes"].pop(0)
        elif ((not summary["S"]["Pers"]) or summary["S"]["Pers"]=='3') and s == "2": 
            if not summary["S"]["Pers"]: summary["S"]["Pers"] = "2"
            if analysis_in["suffixes"][0:1] == ["Pl"]:
                summary["S"]["Num"] = "Pl"
                analysis_in["suffixes"].pop(0)
                if summary["O"]["Pers"] == "0" and inversion == True and summary["Neg"] and summary["Order"] and analysis_in["suffixes"][0:1] == "3": #VTA CNJ THMINV NEG 2 PL 3(PL)
                    summary["O"]["Pers"] == "3"
                    analysis_in["suffixes"].pop()
            elif summary["S"]["Pers"] == "2" and analysis_in["suffixes"][0:2] == ["1", "Pl"]:
                summary["S"]["Num"] = "1Pl"
                analysis_in["suffixes"].pop(0)
                analysis_in["suffixes"].pop(0)
        elif ((not summary["S"]["Pers"]) or summary["S"]["Pers"] == '3') and s == "3":
            summary["S"]["Pers"] = "3"
            if inversion == True and summary["O"]["Pers"] == "0" and summary["Order"] == "Cnj":  summary["O"]["Pers"] = "3'/0" #VTA CNJ THMINV 3
            if analysis_in["suffixes"][0:1] == ["Pl"]:
                summary["S"]["Num"] = "Pl"
                analysis_in["suffixes"].pop(0)
            elif analysis_in["suffixes"][0:1] == ["4"]:
                summary["S"]["Num"] = "Obv"
                analysis_in["suffixes"].pop(0)
        elif ((not summary["S"]["Pers"]) or summary["S"]["Pers"] == "0") and s == "0": 
            summary["S"]["Pers"] = "0"
            if analysis_in["suffixes"][0:1] == ["4"]:
                summary["S"]["Num"] = "Obv"
                analysis_in["suffixes"].pop(0)
            elif analysis_in["suffixes"][0:1] == ["Pl"]:
                summary["S"]["Num"] += "Pl" #NB: += used since 0'Pl is possible
                analysis_in["suffixes"].pop(0)
        elif (not summary["S"]["Pers"]) and s == "X": summary["S"]["Pers"] = "X"
        #}end person/number information from suffixes
        elif summary["Head"].startswith("N") and s == "4": summary["Periph"] = "Obv"
        elif summary["Head"].startswith("N") and s in ["Loc", "Pl"]: summary["Periph"] = s
        else: summary["Else"].append(s)
    if (not summary["S"]["Pers"]) and summary["O"]["Pers"] == "2": summary["S"]["Pers"] = "1" #default person for Thm2a keep at end
    if (not summary["S"]["Pers"]) and summary["O"]["Pers"] == "1": summary["S"]["Pers"] = "2" #default person for Thm1  keep at end
    if not inversion and summary["S"]["Pers"] == "3" and summary["O"]["Pers"] == "3": summary["O"]["Num"] = "Obv" #default obviation for direct themes. should only be necessary for VTA CNJ, which never overtly signals obviation, but kept general
    #summary["Else"] = [y[0] for x in analysis_in for y in analysis_in[x] if not y[1]]
    if inversion == True: summary["S"], summary["O"] = summary["O"], summary["S"]
    return summary

def analysis_dict(analysis_string):
    postags = "\+VAI(O)?|\+VII|\+VTI|\+VTA|\+NA(D)?|\+NI(D)?|\+Conj|\+Interj|\+Num|\+Pron(\+NA|\+NI)|\+Ipc|\+Qnt|\+Adv"
    adict = {"prefix":[], "derivation": [], "preforms":[], "suffixes":[], "clitic":[]}
    adict["clitic"] = [regex.search("((?<=\+)dash\+Adv$)?", analysis_string)[0]]
    analysis_string = regex.sub("\+dash\+Adv", "", analysis_string) #this only needs to happen after clitics are checked and before derivation/suffixes are inspected, stuck with post-clitics
    adict["prefix"] = [regex.search("(^[123X])?", analysis_string)[0]]
    if regex.search("{0}(.*{0})?".format(postags), analysis_string): adict["derivation"] = [x for x in regex.search("{0}(.*{0})?".format(postags), analysis_string)[0].split("+") if x] #Denominal words may contain Dim, etc, but plain nouns will omit this if only POS tags are used as boundaries
    adict["preforms"] = regex.search("(((PV|PN|PA)[^\+]*\+)|Redup\+)*", analysis_string)[0].split("+")
    if regex.search(".*?(?={})".format("|".join([x[2:]+x[:2] for x in postags.split("|")])), "+".join(reversed(analysis_string.split("+")))): adict["suffixes"] = [x for x in reversed(regex.search(".*?(?={})".format("|".join([x[2:]+x[:2] for x in postags.split("|")])), "+".join(reversed(analysis_string.split("+"))))[0].split("+"))]
    if not adict["derivation"]: return None
    return adict

###functions for doing things within the web page

def parse_words(event):
    input_text = pyscript.document.querySelector("#freeNish")
    freeNish = input_text.value
    analyzed = parse_pyhfst("./morphophonologyclitics_analyze.hfstol", *sep_punct(freeNish.lower(), True).split())
    m_parse_lo = [analyzed[w][disambiguate(min_morphs(*analyzed[w]), min_morphs, *analyzed[w])][0] for w in sep_punct(freeNish.lower(), True).split()]
    m_parse_hi = ["'"+formatted(interpret(analysis_dict(x)))+"'" if analysis_dict(x) else "'?'" for x in m_parse_lo]
    lemmata = [x if x else "?" for x in lemmatize(pos_regex, *m_parse_lo)]
    tinies = []
    for l in lemmata:
        try: gloss = gdict[l]
        except KeyError:
            gloss = "?"
        tinies.append("'"+gloss+"'")
    padded = pad(["Original Material:"] + sep_punct(freeNish.lower(), True).split(), ["Narrow Analysis:"] + m_parse_lo, ["Broader Analysis:"] + m_parse_hi, ["Dictionary Entry:"] + lemmata, ["Terse Translation:"] + tinies)
    words_out = "\n".join(["\t".join(p) for p in padded])
    #words_out = tabulate.tabulate([["Word:"] + sep_punct(freeNish.lower(), True).split(), ["Narrow Analysis:"] + m_parse_lo, ["Broad Analysis:"] + m_parse_hi, ["Dictionary Header:"] + lemmata, ["Terse Translation:"] + tinies], tablefmt='html')
    output_div = pyscript.document.querySelector("#output")
    output_div.innerText = words_out 

async def _upload_file_and_analyze(e):
    console.log("Attempted file upload: " + e.target.value)
    file_list = e.target.files
    first_item = file_list.item(0)

    my_bytes: bytes = await get_bytes_from_file(first_item)
    console.log(my_bytes[:10])
    textIn = my_bytes.decode().split('\n')
    console.log(textIn[0])
    analyzed = parse_text(True, *textIn)
    console.log(analyzed[0])
    console.log("I did it!")
    stitched = []
    for i in range(len(textIn)):
        stitched.append(str(i)+'\n')
        stitched.append(textIn[i]+'\n')
        lemmata = [x if x else "?" for x in lemmatize(pos_regex, *analyzed[i])]
        tinies = []
        for l in lemmata:
            try: gloss = gdict[l]
            except KeyError:
                gloss = "?"
            tinies.append("'"+gloss+"'")
        m_parse_hi = ["'"+formatted(interpret(analysis_dict(x)))+"'" if analysis_dict(x) else "'?'" for x in analyzed[i]]
        padded = pad(sep_punct(textIn[i].lower(), True).split(), analyzed[i], m_parse_hi, lemmata, tinies)
        stitched.append(" ".join(padded[0])+'\n')
        stitched.append(" ".join(padded[1])+'\n')
        stitched.append(" ".join(padded[2])+'\n')
        stitched.append(" ".join(padded[3])+'\n')
        stitched.append(" ".join(padded[4])+'\n')
        stitched.append("\n")
    stitched_bytes = "".join(stitched).encode('utf-8')
    #full_output_div = pyscript.document.querySelector("#output_upload")
    #full_output_div.innerText = stitched_bytes
    stitched_stream = io.BytesIO(stitched_bytes)
    js_array = Uint8Array.new(len(stitched_bytes))
    js_array.assign(stitched_stream.getbuffer())

    nu_js_file = File.new([js_array], "unused_file_name.txt", {type: "text/plain"})
    url = URL.createObjectURL(nu_js_file)

    hidden_link = document.createElement("a")
    hidden_link.setAttribute("download", "analyzed_file.txt")
    hidden_link.setAttribute("href", url)
    hidden_link.click()
    #hidden_file.src = window.URL.createObjectURL(nu_js_file)
    #document.getElementById("output_upload").appendChild(hidden_file)

    #new_txt = pyscript.document.createElement('txt')
    #new_txt.src = pyscript.window.URL.createObjectURL(first_item)
    #pyscript.document.getElementById("output_upload").appendChild(new_txt)

async def get_bytes_from_file(file):
    array_buf = await file.arrayBuffer()
    return array_buf.to_bytes()

gdict = mk_glossing_dict(*readin("./copilot_otw2eng.txt"))
pos_regex = "".join(readin("./pos_regex.txt"))
upload_file = pyscript.document.getElementById("file-upload")
add_event_listener(upload_file, "change", _upload_file_and_analyze) #maybe "click" instead of "change"

#data = "this is some text" #"".join(stitched) 
#def downloadFile(*args):
#    encoded_data = data.encode('utf-8')
#    my_stream = io.BytesIO(encoded_data)
#
#    js_array = Uint8Array.new(len(encoded_data))
#    js_array.assign(my_stream.getbuffer())
#
#    nu_js_file = File.new([js_array], "unused_file_name.txt", {type: "text/plain"})
#    url = URL.createObjectURL(nu_js_file)
#
#    hidden_link = document.createElement("a")
#    hidden_link.setAttribute("download", "my_other_file_name.txt")
#    hidden_link.setAttribute("href", url)
#    hidden_link.click()
#
#add_event_listener(document.getElementById("download"), "click", downloadFile)
