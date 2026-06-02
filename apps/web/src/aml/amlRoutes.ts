/** Canonical operations (triage + map split) path; `/` remains a valid alias. */
export const AML_OPERATIONS_PATH = '/triage'

export const AML_PATHS = {
	home: AML_OPERATIONS_PATH,
	map: '/map',
	itdae: '/itdae',
	watchlist: '/watchlist',
	sanctions: '/sanctions',
	incidents: '/incidents',
	audit: '/audit',
	onboarding: '/onboarding',
	admin: '/admin',
	alertDetailPattern: '/alerts/:alertId',
	incidentDetailPattern: '/incidents/:incidentId',
} as const

export const AML_QUERY = {
	mmsi: 'mmsi',
} as const

export function getAlertDetailPath(alertId: number): string {
	return `/alerts/${alertId}`
}

export function getIncidentDetailPath(incidentId: number): string {
	return `/incidents/${incidentId}`
}

export function getMapForMmsiPath(mmsi: string): string {
	return `${AML_OPERATIONS_PATH}?${AML_QUERY.mmsi}=${encodeURIComponent(mmsi)}`
}
