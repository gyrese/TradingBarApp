# Bar Traders — Guide d'utilisation

## C'est quoi Bar Traders ?

Bar Traders est un système de caisse et d'affichage pour bar à concept "Bourse". Les prix des boissons fluctuent automatiquement toutes les 90 secondes, comme sur un marché financier. De temps en temps, un **KRASH** fait chuter tous les prix au minimum pendant 90 secondes — une opportunité pour les clients de commander moins cher.

L'application tourne sur un ordinateur/serveur local. Les appareils du bar (tablettes, TV, téléphones) s'y connectent via le réseau Wi-Fi interne.

---

## Les 4 interfaces

| Interface | URL | Accès | Usage |
|---|---|---|---|
| **The Wall** | `/wall` | Public (sans PIN) | Écran TV affiché aux clients |
| **La Caisse** | `/caisse` | PIN requis | Prise de commande du staff |
| **Admin** | `/admin` | PIN requis | Gestion et configuration |
| **Connexion** | `/login` | — | Saisie du PIN |

> **PIN par défaut : `1234`** — À changer dès la mise en service depuis l'Admin.

---

## The Wall `/wall`

Écran destiné à être affiché sur une TV ou un écran face aux clients.

- Affiche toutes les boissons avec leur **prix actuel** en temps réel
- Un **timer** indique le temps avant la prochaine mise à jour des prix
- Quand un **KRASH** se déclenche, l'écran s'anime et affiche les prix au plancher
- Aucune interaction requise — se met à jour automatiquement via WebSocket
- Pas besoin de PIN pour y accéder

---

## La Caisse `/caisse`

Interface utilisée par le staff pour enregistrer les commandes.

### Enregistrer une vente

1. Appuyer sur le bouton de la boisson commandée
2. Le bouton s'ajoute au panier (côté droit)
3. Appuyer plusieurs fois pour augmenter la quantité, ou utiliser `+` / `-`
4. Sélectionner le mode de paiement : **CB**, **Espèces**, ou **Autre**
5. Appuyer sur **Valider le ticket** — la vente est enregistrée

> Les prix sont **figés au moment du premier ajout au panier**. Si les prix changent pendant la constitution d'une commande, le panier n'est pas affecté.

### Filtrer par catégorie

Les onglets en haut (Bière, Soft, Cocktail…) permettent de filtrer l'affichage. L'onglet **Tous** affiche tout.

### Réordonner les boutons

1. Appuyer sur **✦ Trier** (en haut à droite de la grille)
2. Appuyer-glisser les boutons pour les réorganiser
3. Appuyer sur **✓ Terminer** — l'ordre est sauvegardé définitivement

### Déclencher un KRASH

Appuyer sur le bouton **KRASH 💥** en bas du panneau droit. Une confirmation est demandée. Le KRASH dure 90 secondes (configurable dans l'Admin).

Pour **arrêter** un KRASH en cours, appuyer sur le même bouton devenu **Arrêter le KRASH**.

### Clôture de journée (Rapport Z)

1. Appuyer sur **Rapport Z / Clôture** (icône statistiques)
2. Un récapitulatif s'affiche : total des ventes, ventilation par boisson, par mode de paiement, et détail TVA
3. Bouton **Imprimer** pour imprimer le rapport
4. Bouton **Clôturer Journée (Z)** pour archiver les ventes et remettre les compteurs à zéro

> La clôture est irréversible. Les ventes sont archivées et restent consultables dans l'Admin.

---

## L'Admin `/admin`

Interface de gestion complète, accessible après connexion.

### Tableau de bord

En haut de page : une carte par type de boisson avec le nombre d'articles actifs, et le total des ventes du jour.

### Gérer les boissons

**Ajouter une boisson** — Bouton **Ajouter une boisson** :
- Nom, type (catégorie), icône/emoji ou logo image
- **Prix min** : prix plancher lors des fluctuations normales
- **Prix max** : prix plafond lors des fluctuations normales
- **Prix KRASH** : prix appliqué lors d'un KRASH (doit être ≤ prix min)
- TVA applicable

**Modifier** — Cliquer sur l'icône crayon sur la ligne de la boisson.

**Supprimer** — Cliquer sur l'icône poubelle. La boisson disparaît de la caisse et du Wall.

**Activer / Désactiver** — Une boisson désactivée n'apparaît plus sur la caisse ni sur le Wall mais reste dans la base.

### Gérer les types (catégories)

Section **Types de boissons** : ajouter, renommer ou supprimer des catégories. Chaque type a un nom, une icône emoji et un ordre d'affichage.

### Moteur des prix

Section **Moteur de prix** :
- **Intervalle** : temps en secondes entre chaque mise à jour des prix (défaut : 90s)
- **Durée KRASH** : durée en secondes d'un KRASH (défaut : 90s)
- Bouton **Appliquer** pour sauvegarder, **Redémarrer le moteur** si nécessaire

### Historique des prix

Graphiques de fluctuation par boisson sur les dernières sessions.

### Rapports Z archivés

Consultation des clôtures de journées précédentes avec détail complet des ventes.

### Changer le PIN

Section **Sécurité** : saisir l'ancien PIN, le nouveau (4 à 8 chiffres), confirmer. Applicable immédiatement.

---

## Mécanisme des prix

- Toutes les **90 secondes**, le moteur recalcule un nouveau prix pour chaque boisson, tiré aléatoirement entre son `prix_min` et son `prix_max`, arrondi à 0,10€ près
- Les prix sont mis à jour simultanément sur tous les appareils connectés (Wall, Caisse) via WebSocket
- Le **KRASH** force tous les prix à leur valeur `prix_krash` pendant la durée configurée, puis les prix reprennent leur fluctuation normale

---

## Démarrage du serveur

```bash
python app.py
```

Le serveur démarre sur `http://0.0.0.0:5000`. Sur le réseau local, les appareils y accèdent via l'IP de la machine hôte, ex : `http://192.168.1.10:5000/wall`.

---

## En cas de problème

| Symptôme | Solution |
|---|---|
| Les prix ne se mettent plus à jour | Admin → Moteur de prix → Redémarrer le moteur |
| La caisse affiche "Déconnecté" | Vérifier le Wi-Fi, la page se reconnecte automatiquement |
| Le Wall est figé | Rafraîchir la page (F5) |
| PIN oublié | Modifier directement dans la base : `UPDATE settings SET value='1234' WHERE key='access_pin'` |
| Besoin de repartir de zéro | Supprimer `bar_traders.db` et relancer — la base est recréée avec les boissons par défaut |
