Matteo
1. Wie implementieren wir solche constraints?
     - => filter/reranking

Matteo
2. Welche Constraints
-  

1. Recommmender Implementierung
    - relevant flags (beatmaps)
    - both for random and top users (Eva mentioned she really likes this)
    - use new enjoymet factor of scores (fallback playcount)
    - Be aware of skill improvement of users (use scores after skill stabilization date only, or some post-computation filter for difficulty (not too hard not too easy))
=> performance baseline 

Matteo
1. Constraints einbauen und erneut testen.

Sonja?
1. Ein anderes Datenset finden, inklusive funktionierendem recommender system, constraints überlegen, einbauen und testen.

- Ausschluss kürzlich gekaufter Produkte
Nutzt das Feld reordered in order_products__prior.csv. Alle Artikel, bei denen reordered=1 in den letzten N Bestellungen vorkommt, werden für neue Empfehlungen ausgeschlossen.

- Maximale Artikelzahl pro Abteilung
Greift auf products.csv → department_id (plus departments.csv) zurück. Man kann z.B. höchstens zwei („max_genre_count“) Artikel pro Abteilung („Dairy“, „Produce“, „Bakery“ etc.) pro Empfehlung zulassen.

- Aisle-Diversität
Basierend auf products.csv → aisle_id (plus aisles.csv), erlaubt man pro Empfehlungsliste nur maximal M Artikel aus demselben Gang („Aisle“).


Matteo (anfangen)
3. Präsentation vorbereiten.

