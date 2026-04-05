# Bar Traders - TODO Déploiement Test Bar

## P0 - CRITIQUE (bloquant pour le test)

- [x] Nettoyer `caisse_app.py` : supprimer les 2 classes `CaisseWindow` dupliquées, garder la dernière
- [x] Figer le prix au moment de l'ajout au panier (snapshot via `price_snapshot`, pas référence live)
- [x] Corriger les appels `record_sale()` (paramètres manquants/incorrects)
- [x] Wrapper les opérations DB dans des transactions atomiques (`update_all_prices`, `close_session`)
- [x] Désactiver `debug=True` dans `app.py`
- [x] Déplacer `SECRET_KEY` dans une variable d'environnement (`os.environ` + fallback `os.urandom`)
- [x] Ajouter validation des inputs (prix négatifs, quantités, noms vides, durée KRASH)

## P1 - IMPORTANT (qualité de service)

- [ ] **Restreindre CORS** : remplacer `cors_allowed_origins="*"` par les IPs/origines du réseau local (`app.py:16`)
- [x] Figer les prix sur la caisse web dès l'ajout au panier (snapshot, pas mise à jour live)
- [x] Ajouter support quantité dans la caisse (+/- dans le cart, `changeQuantity()`)
- [x] Corriger formatage prix `wall.html` (`.toFixed(2)` = "5.50€")
- [x] Reconnexion WebSocket automatique + indicateur de connexion (caisse.html)
- [ ] **Indicateur déconnexion sur le Wall** : wall.html n'a pas de `socket.on('disconnect')` — une coupure réseau est invisible sur l'écran public
- [x] Limiter le tableau `priceHistory` en mémoire (limité à 12 dans wall.html)
- [x] Ajouter `try/except` dans `_run_loop` du `price_engine` (crash = plus de MAJ prix)
- [x] Corriger `AudioContext` dans `wall.js` (réutiliser un seul contexte global — fix dans `static/js/wall.js`, le template est inline sans audio)
- [x] Ajouter indexes DB sur `sales(drink_id, sold_at, session_id)`, `price_history(drink_id, recorded_at)`, `tickets(created_at, session_id)`
- [x] Activer `PRAGMA foreign_keys = ON` dans `get_db()`
- [x] Protéger le parsing `krash_end_time` au démarrage (try/except ValueError)

## P2 - RECOMMANDÉ (polish)

- [x] Ajouter politique de rétention `price_history` (purge > 7 jours au init_db)
- [x] Valider durée KRASH (refuser négatif, limiter max 3600s)
- [ ] **Échapper les noms de boissons dans le HTML** : `drink.name` injecté brut dans innerHTML — risque XSS (`caisse.html:1402`, `wall.html`)
- [ ] Ajouter feedback sonore/visuel à la caisse lors d'une vente enregistrée

## DETTE TECHNIQUE (hors-périmètre test mais à noter)

- [ ] `static/js/wall.js` et `static/js/caisse.js` existent mais ne sont **pas chargés** par leurs templates (JS inline dans les HTML) — à nettoyer ou migrer

## TESTS BAR

- [ ] Ventes simultanées multi-barmen (race conditions)
- [ ] Coupure réseau pendant une vente
- [ ] Redémarrage serveur pendant un KRASH (persistance état)
- [ ] MAJ prix pendant constitution du panier (le prix doit rester figé)
- [ ] Charge élevée pendant KRASH (100+ ventes/minute)
- [ ] Affichage Wall sur TV en continu 8h+ (fuites mémoire)
