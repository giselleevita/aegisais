import { useCallback, useState } from 'react'
import './FileDropZone.css'

interface FileDropZoneProps {
    onFileDrop: (file: File) => void
    acceptedTypes?: string[]
    maxSizeMB?: number
}

export default function FileDropZone({ onFileDrop, acceptedTypes = ['.csv', '.dat', '.zst'], maxSizeMB = 1000 }: FileDropZoneProps) {
    const [isDragging, setIsDragging] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [uploadProgress, setUploadProgress] = useState<string>('')

    const validateFile = (file: File): string | null => {
        // Check file extension
        const fileName = file.name.toLowerCase()
        const hasValidExtension = acceptedTypes.some(ext => 
            fileName.endsWith(ext) || 
            fileName.endsWith(ext + '.zst') ||
            fileName.endsWith('.csv.zst') ||
            fileName.endsWith('.dat.zst')
        )

        if (!hasValidExtension) {
            return `File type not supported. Accepted: ${acceptedTypes.join(', ')}`
        }

        // Check file size
        const fileSizeMB = file.size / (1024 * 1024)
        if (fileSizeMB > maxSizeMB) {
            return `File too large. Maximum size: ${maxSizeMB}MB`
        }

        return null
    }

    const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        setIsDragging(false)

        const files = Array.from(e.dataTransfer.files)
        if (files.length === 0) return

        const file = files[0]
        const error = validateFile(file)
        
        if (error) {
            alert(error)
            return
        }

        setIsUploading(true)
        setUploadProgress(`Uploading ${file.name}...`)

        try {
            onFileDrop(file)
            setUploadProgress(`Uploaded ${file.name} successfully!`)
            setTimeout(() => setUploadProgress(''), 2000)
        } catch (err: any) {
            alert(`Upload failed: ${err.message}`)
            setUploadProgress('')
        } finally {
            setIsUploading(false)
        }
    }, [onFileDrop, acceptedTypes, maxSizeMB])

    const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        setIsDragging(true)
    }, [])

    const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        setIsDragging(false)
    }, [])

    const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files
        if (!files || files.length === 0) return

        const file = files[0]
        const error = validateFile(file)
        
        if (error) {
            alert(error)
            return
        }

        setIsUploading(true)
        setUploadProgress(`Uploading ${file.name}...`)

        try {
            onFileDrop(file)
            setUploadProgress(`Uploaded ${file.name} successfully!`)
            setTimeout(() => setUploadProgress(''), 2000)
        } catch (err: any) {
            alert(`Upload failed: ${err.message}`)
            setUploadProgress('')
        } finally {
            setIsUploading(false)
            // Reset input
            e.target.value = ''
        }
    }, [onFileDrop, acceptedTypes, maxSizeMB])

    return (
        <div
            className={`file-drop-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
        >
            <input
                type="file"
                id="file-input"
                className="file-input"
                onChange={handleFileInput}
                accept={acceptedTypes.join(',')}
                disabled={isUploading}
            />
            <label htmlFor="file-input" className="drop-zone-label">
                {isUploading ? (
                    <div className="upload-status">
                        <div className="spinner"></div>
                        <div>{uploadProgress}</div>
                    </div>
                ) : (
                    <>
                        <div className="drop-icon">📁</div>
                        <div className="drop-text">
                            <strong>Drag & drop a file here</strong>
                            <span>or click to browse</span>
                        </div>
                        <div className="drop-hint">
                            Supports: .csv, .dat, .csv.zst, .dat.zst
                        </div>
                    </>
                )}
            </label>
        </div>
    )
}


