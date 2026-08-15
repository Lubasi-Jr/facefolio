import { useQuery } from '@tanstack/react-query'
import { getMyPhotos } from '../api/gallery'

export function useMyPhotos(eventId: string, enabled = true) {
  return useQuery({
    queryKey: ['my-photos', eventId],
    queryFn: () => getMyPhotos(eventId),
    enabled,
  })
}
