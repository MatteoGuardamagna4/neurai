# Note per l'orale

Punti da ripassare prima della difesa: per ognuno la domanda probabile, la risposta breve, i numeri che la
sostengono, una formulazione pronta in inglese e dove trovarlo nel report e nel codice. Il file non entra nel
report (`build.py` legge solo i file `NN_*.md`).

---

## 1. Le costanti di adaptation (0.35 / 0.90 / 0.20)

**Domanda probabile.** "Perché lo scaffolding ha adaptation 0.90? Da dove viene? Il suo vantaggio non è
semplicemente assunto?"

**Risposta breve.** È un'assunzione, non una misura: nessuno studio misura l'adattamento di un tutor su una scala
0–1, quindi non esiste un valore pubblicato. I tre numeri codificano un ordinamento: il tutor di scaffolding si
adatta all'errore del learner più di quanto facciano gli hint fissi o la soluzione completa. Proprio perché è
assunta, l'adaptation è una dimensione della specification curve, e l'esito dipende dallo scenario.

**Come agisce.** Entra solo nell'efficacia F (eq. 2), con peso f₃ = 1.2, e solo negli episodi in cui c'è stato
supporto, cioè dopo una prima risposta sbagliata. Con difficoltà perfettamente adeguata:

| Episodio | F |
|---|---|
| Nessun supporto (tutte le condizioni) | 0.57 |
| Sostituzione (0.20) | 0.63 |
| Tradizionale (0.35) | 0.67 |
| Scaffolding (0.90) | 0.80 |

Conta quindi la distanza tra scaffolding e tradizionale, non il valore assoluto.

**Cosa cambia se l'adaptation fosse diversa** (mediana di G all'anno 10 sulle 216 specifiche di ogni livello):

| Scenario | 0.35 / 0.90 / 0.20 | Dimezzata (0.42 / 0.69 / 0.34) | Uguale per tutti (0.48) |
|---|---|---|---|
| Scaffolding senza fading | 0.013 | 0.007 | **0.000** |
| Scaffolding con fading rapido | 0.073 | 0.062 | 0.051 |
| Sostituzione | −0.152 | −0.152 | −0.151 |

**Il punto da dire bene: non vale per tutti gli scenari allo stesso modo.**
- *Scaffolding senza fading:* l'adaptation decide **se** il vantaggio esiste. Con adaptation uguale è identico
  alla tradizionale (esattamente 0). Il risultato è quindi assunto e il report lo dichiara come tale. Anche nella
  specifica principale vale 0.015, sotto la soglia di 0.02, cioè neutro.
- *Fading rapido:* l'adaptation cambia solo la **dimensione** (da 0.073 a 0.051); il segno resta positivo, perché
  il vantaggio viene dal ritiro del supporto, che cambia gli aggiornamenti di ragionamento e dipendenza.
- *Sostituzione:* l'adaptation non conta (−0.152 contro −0.151), perché il deficit passa dallo sforzo.

**Possibile domanda di seguito.** "Perché la sostituzione ha adaptation più bassa della tradizionale (0.20 contro
0.35)?" Risposta onesta: è una scelta di modellazione non documentata nel repository; la lettura più naturale è che
la soluzione completa non sia calibrata sull'errore specifico del learner. Non incide sui risultati: il deficit della
sostituzione resta −0.15 a tutti e tre i livelli.

**Come dirlo (EN).** "The adaptation constants are assumptions, not measurements: no study measures a tutor's
adaptivity on a zero-to-one scale. That is why we made adaptation a dimension of the specification curve. When all
three protocols share one value, scaffolding without fading becomes numerically identical to traditional
instruction, so its advantage is the assumption itself, and we report it as assumed. Rapid fading and substitution
keep their sign at every level, because they run through support withdrawal and through effort."

**Dove.** Report: Tabella 5 (§3.2.2), eq. 2 (§3.4), Tabella D4 (§3.8 e Appendice D.3), §4.6. Codice:
`config/default.yaml` (`support.adaptation`, `effectiveness.f3`), `config/spec_curve.yaml` (dimensione
`adaptation`). Dati: `outputs/tables/fig8a_spec_curve_G.csv`.

---

## 2. Il plateau della conoscenza (K\* = 0.59 contro 0.96) e la Tabella 7

**Domanda probabile.** "Quanto è realistico il vostro learner? I parametri da dove vengono?" Oppure: "Perché dite che
la dimensione del deficit della sostituzione è un limite superiore?"

**Risposta breve.** I parametri sono assunzioni, fissate all'inizio e confrontate con la letteratura solo dopo le run,
senza cambiarne nessuno. Il confronto mostra che il learner simulato impara più lentamente e dimentica più in fretta
di quanto riporta la letteratura. Per questo le differenze che nascono dallo sforzo, come il deficit della
sostituzione, sono più grandi di quanto sarebbero con parametri realistici: la direzione è il claim, la dimensione è
un limite superiore.

**Il calcolo.** Nell'eq. 9 la conoscenza guadagna αEF(1−K) e perde δK. Si stabilizza dove i due termini si pareggiano:
K\* = αEF / (αEF + δ).

| | Apprendimento per episodio | Oblio per episodio | K\* |
|---|---|---|---|
| Modello | 0.035 (α 0.10 × sforzo 0.65 × efficacia 0.53) | 0.024 | 0.59 |
| Letteratura | 0.217 (punto medio di 0.13–0.30, pyBKT) | 0.0091 (70% trattenuto in un anno, Custers) | 0.96 |

**L'ipotesi da saper difendere.** Nel modello un periodo senza pratica dimentica a un quarto del ritmo del periodo di
lezione, quindi un anno senza pratica vale 52 × 3 × ¼ = 39 episodi. Il 70% di Custers è convertito nello stesso modo
con cui si converte il valore del modello (0.38), così i due lati della tabella usano lo stesso metro: 1 − 0.70^(1/39)
= 0.0091. Il rapporto ¼ è a sua volta un'assunzione: con 1 il plateau della letteratura sarebbe 0.99, con 1/10 sarebbe
0.91. **In ogni caso è molto sopra 0.59.**

**La conseguenza, con un esempio.** Nella run di riferimento la sostituzione ha sforzo medio 0.53 contro 0.71 della
tradizionale, circa un quarto in meno. Con uno sforzo ridotto di un quarto il plateau del modello scende da 0.59 a 0.52
(−0.07); con i parametri della letteratura scenderebbe da 0.96 a 0.95 (−0.01). Nel nostro regime la stessa differenza
di sforzo pesa circa cinque volte di più. (Esempio semplificato: tiene fissa l'efficacia F.)

**Le fonti, verificate sul testo il 27/09.** Custers (2010): "two-third to three-fourth" trattenuto dopo un anno.
pyBKT (Badrinath et al., 2021): learn 0.30 "common values seen for Algebra skills" (nota 5) e 0.134 stimato
nell'esempio. Corbett & Anderson (1995) definiscono p(T) ma non ne riportano valori. Per ω: Ma et al. 0.35, Kulik &
Fletcher 0.66, VanLehn 0.76 (abstract). Per η_M: Rowland 0.50; Adesope 0.61 contro tutti i controlli, 0.51 contro il
ristudio (Tabella 1).

**Se chiedono di ω ("consistent").** Il valore del modello (d = 0.41) sta nel range delle meta-analisi, ma misura una
cosa diversa: la spinta di un hint durante il test, non l'apprendimento misurato in un test successivo. È un confronto
di scala, non di costrutto, e la nota della Tabella 7 lo dice.

**Come dirlo (EN).** "We did not calibrate the parameters; we set them in advance and compared them with published
values afterwards, without changing any. The comparison says our simulated learner learns more slowly and forgets
faster than the evidence on taught knowledge: its knowledge settles at 0.59 of mastery, against 0.96 with published
rates. In that regime a difference in effort matters more, so we claim the direction of the substitution deficit and
read its size as an upper bound."

**Dove.** Report: §3.5 e Tabella 7, §5.1. Codice: `config/parameter_sources.yaml`, `report.parameter_anchors` in
`src/neurotutorsim/report.py`. Dati: `outputs/tables/tableS_parameter_anchors.csv`.
