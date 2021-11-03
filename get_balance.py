import ccxt
import traceback
import argparse


def get_balance_binance_JPY(api_key, api_secret):
    binance = ccxt.binance({'apiKey': str(api_key), 'secret': str(api_secret)})
    coincheck = ccxt.coincheck()

    # Main
    # 1. Get total amount of each currencies
    binance_fetchBalance = binance.fetchBalance()
    asset_balance_binance = binance_fetchBalance['total']

    # 2. Sum lending currencies
    for k in list(asset_balance_binance.keys()):
        if k.startswith('LD'):
            symbol = k.replace('LD', '')
            symbol_amount = asset_balance_binance[k] + asset_balance_binance[symbol]
            asset_balance_binance[symbol] = symbol_amount
            del(asset_balance_binance[k])

    # 3. Exclude amount=0
    for k in list(asset_balance_binance.keys()):
        if asset_balance_binance[k] == 0:
            del(asset_balance_binance[k])

    # 4. Calculate rate for USDT/JPY
    ticker_info_binance = binance.fetch_ticker(symbol='BTC/USDT')
    BTC_USDT = ticker_info_binance['bid']
    ticker_info_coincheck = coincheck.fetch_ticker(symbol='BTC/JPY')
    BTC_JPY = ticker_info_coincheck['bid']
    USDT_JPY = BTC_JPY/BTC_USDT
    print(USDT_JPY, BTC_JPY, BTC_USDT)

    # 5. Calculate net JPY for each currencies
    asset_value = {}
    for k, v in list(asset_balance_binance.items()):

        if k in ('USDT', 'DAI', 'BUSD'):
            asset_value[k] = v*USDT_JPY
            print(k, ": ", asset_value[k])
        else:
            try:
                currency_pair = k + '/USDT'
                ticker_info_binance = binance.fetch_ticker(symbol=currency_pair)
            except Exception:
                try:
                    currency_pair = k + '/BUSD'
                    ticker_info_binance = binance.fetch_ticker(symbol=currency_pair)
                except Exception:
                    print(traceback.format_exc())
            asset_value[k] = v * ticker_info_binance['bid'] * USDT_JPY
            print(k, ": ", asset_value[k])

    total_value_JPY = sum(list(asset_value.values()))
    print("Total: ", total_value_JPY)
    return int(total_value_JPY)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', help='Binance API KEY', action='store')
    parser.add_argument('--api_secret', help='Binance API SECRET', action='store')
    args = parser.parse_args()
    get_balance_binance_JPY(args.api_key, args.api_secret)
