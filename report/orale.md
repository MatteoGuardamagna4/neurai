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

---

## 3. Come si leggono i numeri delle Tabelle 10 e 11

**Domanda probabile.** "Qual è l'unità di misura? −3.37 è tanto o poco? E $G$ = 0.045 cosa vuol dire?"

**Tabella 10 (contrasti corticali predetti).** Unità arbitrarie della risposta BOLD predetta da TRIBE, sommate sui
secondi di lettura (AUC, eq. 26, un valore al secondo). Non è una % di variazione del segnale: il valore assoluto non ha
significato, conta solo il confronto con la variabilità dello stesso output. Per scala: la deviazione standard
dell'AUC di rete tra i 90 testi è circa 2.8 (media sulle sette reti); nella dorsal attention è circa 4. Quindi lo S − T
della dorsal attention (−3.37) è grande più o meno quanto la differenza tipica tra due lezioni qualsiasi in quella rete.

**Tabella 11 (contrasti a 10 anni).** Tutte differenze su scala 0–1, di due tipi:
- $G$ è sulla scala degli stati del learner (conoscenza, ragionamento, memoria, dipendenza: grandezze latenti tra 0 e
  1). È la media dei quattro contrasti, con la dipendenza col segno invertito. Esempio, rapid fading: K +0.014,
  R +0.101, M −0.023, D −0.088, quindi (0.014 + 0.101 − 0.023 + 0.088) / 4 ≈ 0.045.
- Le altre colonne sono probabilità (di rispondere giusto, di chiedere aiuto): 0.01 = un punto percentuale. La
  sostituzione ha −0.175 in unaided accuracy, cioè 17.5 punti in meno. Il far transfer tradizionale a 10 anni è circa
  0.47, quindi il −0.134 della sostituzione è quasi un terzo in meno.

**Come dirlo (EN).** "The cortical contrasts are in arbitrary units of the predicted BOLD signal summed over the
seconds of reading, so only relative size matters: the scaffolding contrast in the dorsal attention network is about
as large as the typical difference between two different lessons. The ten-year contrasts are differences on a
zero-to-one scale: for the test outcomes, 0.01 is one percentage point; G averages the four state contrasts, with
dependence counted as a cost."

**Dove.** Report: didascalie delle Tabelle 10 e 11 (§4.1, §4.3), Tabella B1 e eq. 26 (Appendice B), eq. 16 (§3.7).
Dati: `data/tribe/tribe_main/wpm220/tribe_metrics.parquet`, `outputs/tables/table5_scenario_contrasts_v_main.csv`.

---

## 4. Il diagramma di fase: cosa aggiunge rispetto agli scenari

**Domanda probabile.** "Se avete già confrontato scaffolding e sostituzione nella run a 10 anni, a cosa serve il
diagramma di fase?"

**Risposta breve.** Gli scenari con nome sono due punti della mappa, e differiscono in due cose insieme: la
sostituzione dà la risposta *e* ha adaptation più bassa (0.20 contro 0.90). Confrontandoli non si sa quale delle due
produce il gap. La mappa le separa: un protocollo AI con tre manopole, adaptation $a$, sforzo conservato $e$,
probabilità di dare la risposta $o$ (7 × 7 × 3 = 147 protocolli, 100 draw × 300 learner ciascuno).

**Cosa mostra.**
- I due scenari ritornano come angoli della mappa: a $o$ = 1, $e$ = 0 la $G$ è −0.192/−0.195 (a = 0.25/0.10) contro
  −0.191 della sostituzione; a $o$ = 0, $e$ = 0 è 0.014/0.017 (a = 0.85/1.00) contro 0.015 dello scaffolding senza
  fading. È anche un controllo di coerenza (run diverse, stessa risposta).
- Una sostituzione con adaptation massima (a = 1) resta a −0.179: l'adaptation spiega poco, **dare la risposta spiega
  quasi tutto**.
- Conservare lo sforzo ($e$ da 0 a 1) più che dimezza il danno (da −0.195 a −0.110 con a = 0.10; da −0.179 a −0.081
  con a = 1), ma non lo annulla mai: il resto passa da offloading e dipendenza.
- Senza risposte ($o$ = 0) tutte le celle sono neutre; con $o$ = 0.5 o 1 tutte dannose.
- Il tipping point: basta circa 1 episodio AI su 10 che dà la risposta ($o$ = 0.097, intervallo 0.058–0.144) per
  portare lo scaffolding sotto la tradizionale. Nessuno scenario con nome può dirlo: $o$ vi vale solo 0 o 1, ed $e$
  sempre 0.
- Differenza col free choice: lì la miscela di protocolli la sceglie il learner in base al suo stato (selezione);
  nella mappa la miscela è casuale, quindi isola la "dose" di risposte.

**Cautela.** È una conseguenza delle assunzioni (ricevere la risposta toglie sforzo, aumenta offloading e dipendenza),
non un'osservazione; e l'effetto dell'adaptation a $o$ = 0 è assunto per costruzione.

**Come dirlo (EN).** "The named scenarios are two corners of the map, and they differ in two things at once:
substitution supplies the answer and is also less adaptive. The map separates the two. A substitution protocol with
maximal adaptation is still clearly harmful, while a tutor that never supplies answers is neutral whatever its
adaptation. Within the model, what decides the sign is whether the AI hands out answers, and about one AI episode in
ten is enough to tip scaffolding below traditional instruction."

**Dove.** Report: §4.4 e Figura 6, §3.7 (Tabella 8). Codice: `frontier_scenarios` in
`src/neurotutorsim/longitudinal.py`. Dati: `outputs/tables/fig7a_phase_diagram.csv`, `tableS_tipping_points.csv`.

---

## 5. La decomposizione dei meccanismi

**Domanda probabile.** "Perché la sostituzione fa peggio? Attraverso cosa?"

**Il metodo in una frase.** Si rifà girare lo scenario congelando un ingrediente alla volta al valore che lo stesso
learner aveva, nello stesso episodio, con l'istruzione tradizionale; la quota di gap che sparisce è il contributo di
quell'ingrediente: 1 − (gap congelato / gap pieno). Tre canali: sforzo E ed efficacia F nell'aggiornamento della
conoscenza, dipendenza D nelle decisioni (chiedere aiuto, scegliere il protocollo). Quattro scenari: tutti tranne il
free choice con la regola fittata.

**I risultati (Tabella E4).**
- *Sostituzione:* congelando lo sforzo sparisce 0.97 del gap di conoscenza ma solo 0.51 di $G$, perché E e F sono
  congelati solo nell'aggiornamento della conoscenza, e ragionamento, memoria e dipendenza vengono colpiti per altre vie
  (offloading, nessun tentativo proprio). La dipendenza dà 0: non c'è aiuto da chiedere.
- *Scaffolding senza fading:* l'efficacia porta tutto (1.00), perché l'adaptation, che entra da F, è l'unica
  differenza con la tradizionale.
- *Rapid fading:* nessun canale supera 0.22 di $G$; il resto viene dal ritiro dell'aiuto, che agisce direttamente su
  ragionamento e dipendenza.
- *Free choice:* efficacia −0.12 su $G$ (congelarla allarga il gap: lavorava a favore dello scenario), sforzo 1.25
  sulla conoscenza (più di tutto il gap, perché un altro canale spinge in senso opposto). Le quote non sommano a 1
  perché i canali si alimentano a vicenda nel tempo (anche nello scaffolding senza fading: 0.10 + 0.13 + 1.00).

**Cautela.** È una scomposizione dentro il modello, non un'analisi di mediazione causale (§3.7).

**Come dirlo (EN).** "We reran each scenario holding one channel at the value the same learner had under traditional
instruction. For substitution, holding effort removes almost the whole knowledge deficit: in the model, learners who
are given the answer learn less because they work less. For scaffolding without fading the whole contrast runs through
effectiveness, which is where the assumed adaptation enters. This decomposes the model; it is not a causal mediation
analysis."

**Dove.** Report: §4.5, Tabella E4 (Appendice E), Tabella 8 (§3.7). Codice: `mediation_scenarios` e il blocco
`med_E`/`med_F` in `src/neurotutorsim/longitudinal.py`. Dati: `outputs/tables/tableS_mechanism_decomposition.csv`.
