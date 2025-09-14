"""
Legal Document Management Module
Integrates with main Flask app
"""
import os
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class LegalDocManager:
    def __init__(self, upload_folder="uploads/legal_docs"):
        self.upload_folder = upload_folder
        self.allowed_extensions = {'.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'}
        os.makedirs(upload_folder, exist_ok=True)
        
    def upload_document(self, file, client_name, matter_description, user_email):
        """Upload and store a legal document"""
        try:
            if not self._allowed_file(file.filename):
                return {"error": "File type not allowed"}
            
            # Generate unique filename
            file_hash = hashlib.md5(f"{file.filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
            filename = f"{file_hash}_{file.filename}"
            filepath = os.path.join(self.upload_folder, filename)
            
            # Save file
            file.save(filepath)
            
            # Get file size
            file_size = os.path.getsize(filepath)
            file_size_str = self._format_file_size(file_size)
            
            # Determine document type
            doc_type = self._classify_document(file.filename)
            
            # Create document record
            document = {
                'id': file_hash,
                'original_name': file.filename,
                'stored_name': filename,
                'client': client_name,
                'matter': matter_description,
                'type': doc_type,
                'date_uploaded': datetime.now().isoformat(),
                'file_size': file_size_str,
                'file_path': filepath,
                'status': 'New',
                'uploaded_by': user_email
            }
            
            return {"success": True, "document": document}
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            return {"error": f"Upload failed: {str(e)}"}
    
    def get_documents(self, user_email=None, client_filter=None, type_filter=None, search_term=None):
        """Get filtered list of documents"""
        try:
            # In production, this would query your database
            # For now, return mock data based on filters
            documents = self._get_mock_documents()
            
            # Apply filters
            if client_filter and client_filter != "All":
                documents = [doc for doc in documents if doc['client'] == client_filter]
            
            if type_filter and type_filter != "All":
                documents = [doc for doc in documents if doc['type'] == type_filter]
            
            if search_term:
                search_lower = search_term.lower()
                documents = [doc for doc in documents if 
                           search_lower in doc['original_name'].lower() or 
                           search_lower in doc['client'].lower() or
                           search_lower in doc['matter'].lower()]
            
            return {"success": True, "documents": documents}
            
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            return {"error": f"Failed to retrieve documents: {str(e)}"}
    
    def get_document_content(self, document_id):
        """Get document content for viewing/downloading"""
        try:
            # In production, find document by ID in database
            document = self._find_document_by_id(document_id)
            if not document:
                return {"error": "Document not found"}
            
            filepath = document.get('file_path')
            if not filepath or not os.path.exists(filepath):
                return {"error": "Document file not found"}
            
            with open(filepath, 'rb') as f:
                content = f.read()
            
            return {
                "success": True, 
                "content": content, 
                "filename": document['original_name'],
                "mime_type": self._get_mime_type(document['original_name'])
            }
            
        except Exception as e:
            logger.error(f"Error getting document content: {str(e)}")
            return {"error": f"Failed to retrieve document: {str(e)}"}
    
    def delete_document(self, document_id, user_email):
        """Delete a document"""
        try:
            document = self._find_document_by_id(document_id)
            if not document:
                return {"error": "Document not found"}
            
            # Check permissions (user can only delete their own docs)
            if document.get('uploaded_by') != user_email:
                return {"error": "Permission denied"}
            
            # Delete file
            filepath = document.get('file_path')
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            
            # In production, delete from database
            return {"success": True, "message": "Document deleted successfully"}
            
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return {"error": f"Failed to delete document: {str(e)}"}
    
    def get_client_list(self, user_email):
        """Get list of clients for the user"""
        try:
            # Mock client data - in production, query database
            clients = [
                {"name": "John Smith", "type": "Individual", "active_matters": 1},
                {"name": "TechCorp LLC", "type": "Business", "active_matters": 2},
                {"name": "Mary Johnson", "type": "Individual", "active_matters": 1},
                {"name": "Sarah Williams", "type": "Individual", "active_matters": 1},
                {"name": "ABC Partners", "type": "Business", "active_matters": 1}
            ]
            
            return {"success": True, "clients": clients}
            
        except Exception as e:
            logger.error(f"Error getting clients: {str(e)}")
            return {"error": f"Failed to retrieve clients: {str(e)}"}
    
    def add_client(self, client_name, client_type, user_email):
        """Add a new client"""
        try:
            if not client_name or not client_type:
                return {"error": "Client name and type are required"}
            
            client = {
                "name": client_name,
                "type": client_type,
                "active_matters": 0,
                "created_by": user_email,
                "created_date": datetime.now().isoformat()
            }
            
            # In production, save to database
            return {"success": True, "client": client}
            
        except Exception as e:
            logger.error(f"Error adding client: {str(e)}")
            return {"error": f"Failed to add client: {str(e)}"}
    
    def get_time_entries(self, user_email, client_filter=None):
        """Get time tracking entries"""
        try:
            # Mock time entries - in production, query database
            entries = [
                {
                    "id": 1,
                    "date": "2024-01-15",
                    "client": "John Smith",
                    "hours": 2.5,
                    "description": "Document review and client consultation",
                    "rate": 250.0,
                    "amount": 625.0
                },
                {
                    "id": 2,
                    "date": "2024-01-16", 
                    "client": "TechCorp LLC",
                    "hours": 1.0,
                    "description": "Contract drafting",
                    "rate": 275.0,
                    "amount": 275.0
                }
            ]
            
            if client_filter and client_filter != "All":
                entries = [e for e in entries if e['client'] == client_filter]
            
            return {"success": True, "entries": entries}
            
        except Exception as e:
            logger.error(f"Error getting time entries: {str(e)}")
            return {"error": f"Failed to retrieve time entries: {str(e)}"}
    
    def add_time_entry(self, entry_data, user_email):
        """Add a time tracking entry"""
        try:
            required_fields = ['date', 'client', 'hours', 'description', 'rate']
            for field in required_fields:
                if field not in entry_data or not entry_data[field]:
                    return {"error": f"Field '{field}' is required"}
            
            entry = {
                "id": len(self._get_mock_time_entries()) + 1,
                "date": entry_data['date'],
                "client": entry_data['client'],
                "hours": float(entry_data['hours']),
                "description": entry_data['description'],
                "rate": float(entry_data['rate']),
                "amount": float(entry_data['hours']) * float(entry_data['rate']),
                "created_by": user_email,
                "created_date": datetime.now().isoformat()
            }
            
            # In production, save to database
            return {"success": True, "entry": entry}
            
        except Exception as e:
            logger.error(f"Error adding time entry: {str(e)}")
            return {"error": f"Failed to add time entry: {str(e)}"}
    
    def get_analytics(self, user_email, start_date=None, end_date=None):
        """Get analytics and reports"""
        try:
            documents = self._get_mock_documents()
            time_entries = self._get_mock_time_entries()
            
            # Document statistics
            doc_types = {}
            client_docs = {}
            for doc in documents:
                doc_types[doc['type']] = doc_types.get(doc['type'], 0) + 1
                client_docs[doc['client']] = client_docs.get(doc['client'], 0) + 1
            
            # Time tracking statistics
            total_hours = sum(entry['hours'] for entry in time_entries)
            total_revenue = sum(entry['amount'] for entry in time_entries)
            avg_rate = total_revenue / total_hours if total_hours > 0 else 0
            
            analytics = {
                "document_stats": {
                    "total_documents": len(documents),
                    "by_type": doc_types,
                    "by_client": client_docs
                },
                "time_stats": {
                    "total_hours": total_hours,
                    "total_revenue": total_revenue,
                    "average_rate": avg_rate,
                    "entries_count": len(time_entries)
                }
            }
            
            return {"success": True, "analytics": analytics}
            
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return {"error": f"Failed to retrieve analytics: {str(e)}"}
    
    def _allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and os.path.splitext(filename)[1].lower() in self.allowed_extensions
    
    def _format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _classify_document(self, filename):
        """Classify document type based on filename"""
        filename_lower = filename.lower()
        if "contract" in filename_lower or "agreement" in filename_lower:
            return "Contract"
        elif "motion" in filename_lower or "complaint" in filename_lower:
            return "Court Motion"
        elif "llc" in filename_lower or "incorporation" in filename_lower:
            return "Articles of Incorporation"
        elif "lease" in filename_lower:
            return "Lease Agreement"
        elif "employment" in filename_lower:
            return "Employment Contract"
        else:
            return "General Document"
    
    def _get_mime_type(self, filename):
        """Get MIME type for file"""
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def _get_mock_documents(self):
        """Mock document data - replace with database query in production"""
        return [
            {
                'id': 'doc001',
                'original_name': 'Divorce_Settlement_Agreement_Smith.pdf',
                'stored_name': 'doc001_Divorce_Settlement_Agreement_Smith.pdf',
                'client': 'John Smith',
                'matter': 'Divorce Proceedings',
                'type': 'Settlement Agreement',
                'date_uploaded': '2024-01-15',
                'file_size': '2.1 MB',
                'status': 'Final',
                'uploaded_by': 'user@example.com'
            },
            {
                'id': 'doc002',
                'original_name': 'LLC_Formation_TechCorp.pdf',
                'stored_name': 'doc002_LLC_Formation_TechCorp.pdf',
                'client': 'TechCorp LLC',
                'matter': 'Business Formation',
                'type': 'Articles of Incorporation',
                'date_uploaded': '2024-01-20',
                'file_size': '1.8 MB',
                'status': 'Draft',
                'uploaded_by': 'user@example.com'
            }
        ]
    
    def _get_mock_time_entries(self):
        """Mock time entry data - replace with database query in production"""
        return [
            {
                "id": 1,
                "date": "2024-01-15",
                "client": "John Smith", 
                "hours": 2.5,
                "description": "Document review and client consultation",
                "rate": 250.0,
                "amount": 625.0
            }
        ]
    
    def _find_document_by_id(self, document_id):
        """Find document by ID - replace with database query in production"""
        documents = self._get_mock_documents()
        return next((doc for doc in documents if doc['id'] == document_id), None)