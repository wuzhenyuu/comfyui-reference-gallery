"""Opt-in live regression against an isolated, CPU-only ComfyUI instance.

Set COSTUME_CACHE_TEST_URL=http://127.0.0.1:8191 before running this file.
The test submits only a local reference-image node and PreviewImage; no model
is loaded and no external generation service is contacted.
"""
import asyncio
import json
import os
import unittest
import uuid

import aiohttp


BASE_URL = os.environ.get("COSTUME_CACHE_TEST_URL", "").rstrip("/")


@unittest.skipUnless(BASE_URL, "Set COSTUME_CACHE_TEST_URL to an isolated ComfyUI test server")
class CacheReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_seed_cached_ui_is_replayed_to_a_fresh_client(self):
        prompt = {
            "3": {"class_type": "RandomCostumeGallery", "inputs": {
                "library": "all", "category": "all", "query": "", "seed": 42, "language": "zh"}},
            "4": {"class_type": "PreviewImage", "inputs": {"images": ["3", 0]}},
        }
        timeout = aiohttp.ClientTimeout(total=40)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async def run_prompt():
                # A fresh socket/client ID models opening the same workflow in
                # a new browser after another client's execution populated cache.
                client_id = str(uuid.uuid4())
                messages = []
                async with session.ws_connect(BASE_URL + "/ws", params={"clientId": client_id}) as socket:
                    async with session.post(BASE_URL + "/prompt", json={"client_id": client_id, "prompt": prompt}) as response:
                        queued = await response.json()
                        self.assertEqual(response.status, 200, queued)
                    prompt_id = queued["prompt_id"]
                    async with asyncio.timeout(30):
                        async for message in socket:
                            if message.type != aiohttp.WSMsgType.TEXT:
                                continue
                            event = json.loads(message.data)
                            data = event.get("data", {})
                            if data.get("prompt_id") != prompt_id:
                                continue
                            messages.append(event)
                            self.assertNotIn(event["type"], ("execution_error", "execution_interrupted"), event)
                            if event["type"] == "execution_success":
                                break
                        history = None
                        for _ in range(100):
                            async with session.get(BASE_URL + "/history/" + prompt_id) as response:
                                histories = await response.json()
                            if prompt_id in histories:
                                history = histories[prompt_id]
                                break
                            await asyncio.sleep(0.05)
                        self.assertIsNotNone(history, "Completed prompt was not published to history")
                return prompt_id, messages, history

            first_id, first_events, first_history = await run_prompt()
            second_id, second_events, second_history = await run_prompt()
        self.assertTrue(first_history["status"]["completed"])
        self.assertTrue(second_history["status"]["completed"])
        first_identity = first_history["outputs"]["3"]["costume_id"]
        self.assertEqual(first_identity, second_history["outputs"]["3"]["costume_id"])
        self.assertEqual(first_history["outputs"]["4"]["images"], second_history["outputs"]["4"]["images"])
        cached_nodes = {node for event in second_events if event["type"] == "execution_cached"
                        for node in event["data"]["nodes"]}
        self.assertIn("3", cached_nodes)
        replayed = [event for event in second_events
                    if event["type"] == "executed" and event["data"].get("node") == "3"]
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0]["data"]["output"]["costume_id"], first_identity)
        print(json.dumps({"first_prompt_id": first_id, "second_prompt_id": second_id,
                          "first_cached_nodes": [event["data"]["nodes"] for event in first_events
                                                 if event["type"] == "execution_cached"],
                          "second_cached_nodes": sorted(cached_nodes), "costume_id": first_identity,
                          "second_history_output_nodes": sorted(second_history["outputs"]),
                          "cached_random_executed_events": len(replayed),
                          "preview_image": second_history["outputs"]["4"]["images"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    unittest.main()
