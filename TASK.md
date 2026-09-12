Implement this Python function only:

    def match_orders(buys, sells):
        ...

Each order is a dict:
    {"id": str, "price": int, "qty": int, "ts": int}

Rules:
1. Ignore orders with qty <= 0.
2. Buy priority: higher price first, then lower ts, then id ascending.
3. Sell priority: lower price first, then lower ts, then id ascending.
4. Match while best_buy.price >= best_sell.price.
5. Support partial fills.
6. Trade price is the older order's price (lower ts). If timestamps are equal,
   use the sell order's price for deterministic behavior.
7. Do not mutate the input lists or their dicts.
8. Return exactly:
   {
     "trades": [
        {"buy_id": str, "sell_id": str, "price": int, "qty": int}, ...
     ],
     "buys": [remaining buy dicts in priority order],
     "sells": [remaining sell dicts in priority order]
   }
9. The remaining order dicts must preserve id/price/ts and contain the residual qty.
10. Use only the Python standard library.
