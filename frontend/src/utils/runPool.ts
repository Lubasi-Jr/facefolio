export function runPool<T>(
  items: T[],
  worker: (item: T) => Promise<void>,
  concurrency: number
): Promise<void> {
  return new Promise((resolve) => {
    if (items.length === 0) {
      resolve()
      return
    }

    let nextIndex = 0
    let completed = 0

    const startNext = () => {
      if (nextIndex >= items.length) return
      const item = items[nextIndex]
      nextIndex += 1

      worker(item)
        .catch(() => {})
        .finally(() => {
          completed += 1
          if (completed === items.length) {
            resolve()
          } else {
            startNext()
          }
        })
    }

    const initialWorkers = Math.min(concurrency, items.length)
    for (let i = 0; i < initialWorkers; i++) {
      startNext()
    }
  })
}
