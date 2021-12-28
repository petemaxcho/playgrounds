from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util.ints import uint32, uint16
from chia.util.config import load_config
from time import localtime, struct_time
from typing import List, Optional
from chia.consensus.block_record import BlockRecord
from chia.types.blockchain_format.coin import Coin
from chia.types.coin_record import CoinRecord

import chia.util.bech32m as b
import asyncio
from pathlib import Path
import os

async def main() -> None:
    rpc_port: uint16 = uint16(8155)
    self_hostname = "localhost"
    path = Path(os.path.expanduser(os.getenv("STOR_ROOT", "~/.stor/mainnet"))).resolve()
    config = load_config(path, "config.yaml")
    all_the_puzzles = []
    puzzleBalances = dict()

    client = await FullNodeRpcClient.create(self_hostname, rpc_port, path, config)
    try:
        blockchain_state = await client.get_blockchain_state()
        if blockchain_state is None:
            print("There is no blockchain...")
            return None
        peak: Optional[BlockRecord] = blockchain_state["peak"]
        print(peak.height)

        print("Proceeding through blockchain...")
        for i in range(peak.height):
            block_result = (await client.get_block_record_by_height(i))
            print(f"{block_result.height} {block_result.height/peak.height}")

            if block_result.reward_claims_incorporated is not None:
                for reward in block_result.reward_claims_incorporated:
                    all_the_puzzles.append(reward.puzzle_hash)

            block_adds_and_rems = (await client.get_additions_and_removals(block_result.header_hash))
            addCoins: Optional[CoinRecord] = block_adds_and_rems[0]
            for c in addCoins:
                all_the_puzzles.append(c.coin.puzzle_hash)
            
            remCoins: Optional[CoinRecord] = block_adds_and_rems[1]
            for c in remCoins:
                all_the_puzzles.append(c.coin.puzzle_hash)
            
        print("Removing duplicate puzzles...")
        clean_puzzle_hashes = list(dict.fromkeys(all_the_puzzles))
        print("Scanning puzzles...")
        for idx, ph in enumerate(clean_puzzle_hashes):
            count = clean_puzzle_hashes.count
            print(f"{ph} {idx} of {count}")
            coin_records: Optional[CoinRecord] = (await client.get_coin_records_by_puzzle_hash(ph))
            sum = 0
            for c in coin_records:
                if c.spent == False:
                    sum = sum + c.coin.amount
            cSum = sum / 1000000000000.0
            phAddr = b.encode_puzzle_hash(bytes.fromhex(f"{ph}"), "stor")
            puzzleBalances[ph] = cSum

        print("Sorting puzzles...")
        sortedPuzBal = sorted(puzzleBalances.items(), key=lambda x: x[1])#, reverse=True) 
        print("Printing ranking:")
        for puzz in sortedPuzBal:
            phAddr = b.encode_puzzle_hash(bytes.fromhex(f"{puzz[0]}"), "stor") 
            print(f"{phAddr} {puzz[0]} {puzz[1]}")

    finally:
        client.close()

asyncio.run(main())