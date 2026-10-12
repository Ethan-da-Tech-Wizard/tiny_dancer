# CPU-thread comparison

Completed 2026-10-11. **Keep eight production threads:** neither candidate passed the declared speed criterion. All 377 regression checks passed; actual agent qualification remains failed.

The final comparison completed in 662.533 seconds, within its 720-second limit. The first attempt stopped after its 45-second cooling window was insufficient; it remains in the result history. Only the cooling allowance changed to 120 seconds for the second attempt.

| Run | Median time per 384-token turn | Median model CPU utilization | Peak CPU / GPU temperature | Thermal flag samples |
| --- | ---: | ---: | --- | ---: |
| 8 threads · first baseline | 13.018 s | 506.3% | 98°C / 86°C | 0 / 52 |
| 4 threads | 16.202 s | 315.2% | 98°C / 87°C | 1 / 57 |
| 6 threads | 13.845 s | 416.3% | 97°C / 87°C | 5 / 54 |
| 8 threads · repeat baseline | 13.433 s | 495.4% | 97°C / 87°C | 6 / 51 |

CPU utilization counts 100% per logical CPU; it is model-process activity, not whole-computer utilization or measured power consumption. Four threads used about 37% less CPU but took 22.5% longer per measured turn. Six used about 17% less CPU but took 4.7% longer. Comparisons use the mean of the two baseline medians. Neither candidate was at least 5% faster than both baselines.

All twelve measured output-token sequences matched. Starting GPU temperatures were 68/72/72/72°C and CPU temperatures 77/75/75/75°C, within the predeclared spreads. Minimum available system RAM was 6.514 GiB and peak total GPU memory 5085 MiB. Model private-memory peaks were about 6.64–6.68 GiB; this does not establish a memory reduction.

Same native MXFP4 GPT-OSS-20B weights, precision, context 8192, CPU expert placement 16, CUDA/KV/batch and greedy sampler throughout. Both generation and prompt-processing CPU thread counts varied. Each owned session had a 128-token warmup and three repeated final-channel turns capped at 384 tokens. No private reasoning was recorded, no OS caches were dropped, and no host power/fan setting or unrelated process was changed. The benchmark released its owned models; the app is idle.

These are warm repeated-prompt measurements. Median physical reads during those turns were 0 MiB for both baselines/four threads and about 1.13 MiB for six. They do not characterize the tens of gigabytes of reads seen during prior varied native agent tasks. Brief thermal-flag activation and temperature/order effects remain practical limits; this is not a general throughput or desktop-responsiveness guarantee.

Next performance investigation: measure prompt-processing, generation, paging and thermal flags together across a frozen sequence of varied contexts. The previous disk-heavy observations motivate that experiment; reducing CPU threads did not establish a speed improvement. Any expert-cache or asynchronous-I/O implementation needs distinct-expert numerical routing/cache tests before native task trials.

[Machine-readable comparison](cpu-thread-validation.json), [control checks](cpu-thread-controls-validation.json), [all 377 named tests](validation/runs/20261011T181017428893Z.json), [current and historical results](TEST_RESULTS.md), [research sources](OPEN_SOURCE_RESEARCH.md), [native qualification](NATIVE_QUALIFICATION.md).

The benchmark and tests are original Apache-2.0 project code using existing dependencies. No package, framework or external inference service was added. The existing license check verified 257 texts, 45 Python distributions and 29 direct host dependencies.
