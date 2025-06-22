#!/usr/bin/env python3
"""
Dependency Analyzer for Slide Extractor Project
Analyzes and visualizes project dependencies across different configurations
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DependencyAnalyzer:
    """Analyzes project dependencies across multiple requirement files"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.requirement_files = {
            "main": "requirements.txt",
            "gradio": "requirements_gradio.txt", 
            "robust": "requirements_robust.txt"
        }
        self.dependencies = {}
        self.conflicts = []
        self.security_issues = []
        
    def parse_requirements_file(self, filepath: str) -> Dict[str, str]:
        """Parse a requirements file and return package:version mapping"""
        dependencies = {}
        
        if not os.path.exists(filepath):
            logger.warning(f"Requirements file not found: {filepath}")
            return dependencies
            
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                    
                # Parse package name and version
                if '>=' in line:
                    package, version = line.split('>=', 1)
                elif '==' in line:
                    package, version = line.split('==', 1)
                elif '>' in line:
                    package, version = line.split('>', 1)
                else:
                    package = line
                    version = "any"
                    
                # Clean package name
                package = package.strip()
                version = version.strip()
                
                # Handle extras (e.g., celery[redis])
                if '[' in package:
                    package = package.split('[')[0]
                    
                dependencies[package] = version
                
        return dependencies
    
    def analyze_all_requirements(self):
        """Analyze all requirement files"""
        logger.info("🔍 Analyzing requirement files...")
        
        for config_name, filename in self.requirement_files.items():
            filepath = self.project_root / filename
            deps = self.parse_requirements_file(str(filepath))
            self.dependencies[config_name] = deps
            logger.info(f"✅ {config_name}: {len(deps)} packages")
    
    def find_conflicts(self):
        """Find version conflicts between different configurations"""
        logger.info("🔍 Checking for version conflicts...")
        
        all_packages = set()
        for deps in self.dependencies.values():
            all_packages.update(deps.keys())
            
        for package in all_packages:
            versions = {}
            for config, deps in self.dependencies.items():
                if package in deps:
                    versions[config] = deps[package]
                    
            if len(versions) > 1:
                unique_versions = set(versions.values())
                if len(unique_versions) > 1:
                    self.conflicts.append({
                        'package': package,
                        'versions': versions
                    })
    
    def get_installed_packages(self) -> Dict[str, str]:
        """Get currently installed packages"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=freeze'], 
                                  capture_output=True, text=True)
            installed = {}
            
            for line in result.stdout.split('\n'):
                if '==' in line:
                    package, version = line.split('==', 1)
                    installed[package.lower()] = version
                    
            return installed
        except Exception as e:
            logger.error(f"Error getting installed packages: {e}")
            return {}
    
    def check_security_vulnerabilities(self):
        """Check for known security vulnerabilities"""
        logger.info("🔒 Checking for security vulnerabilities...")
        
        try:
            # Try to use pip-audit if available
            result = subprocess.run([sys.executable, '-m', 'pip', 'audit'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse audit output
                for line in result.stdout.split('\n'):
                    if 'vulnerability' in line.lower():
                        self.security_issues.append(line.strip())
            else:
                logger.info("pip-audit not available, skipping vulnerability check")
                
        except Exception as e:
            logger.warning(f"Security check failed: {e}")
    
    def analyze_import_usage(self) -> Dict[str, List[str]]:
        """Analyze which packages are actually imported in the code"""
        logger.info("📊 Analyzing import usage...")
        
        import_usage = defaultdict(list)
        python_files = list(self.project_root.glob("*.py"))
        
        # Common package name mappings
        package_mappings = {
            'opencv-python': 'cv2',
            'opencv-contrib-python': 'cv2', 
            'pillow': 'PIL',
            'scikit-image': 'skimage',
            'scikit-learn': 'sklearn',
            'beautifulsoup4': 'bs4',
            'python-dotenv': 'dotenv',
            'google-generativeai': 'google.generativeai'
        }
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find import statements
                import_pattern = r'^(?:from\s+(\S+)|import\s+(\S+))'
                matches = re.findall(import_pattern, content, re.MULTILINE)
                
                for match in matches:
                    module = match[0] or match[1]
                    if module:
                        # Get top-level module
                        top_module = module.split('.')[0]
                        import_usage[top_module].append(str(py_file.name))
                        
            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")
                
        return dict(import_usage)
    
    def generate_dependency_tree(self) -> Dict[str, List[str]]:
        """Generate dependency tree for installed packages"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', '--verbose'], 
                                  capture_output=True, text=True)
            # This is a simplified version - full implementation would parse pip show output
            return {}
        except Exception:
            return {}
    
    def generate_report(self) -> Dict:
        """Generate comprehensive dependency analysis report"""
        logger.info("📋 Generating analysis report...")
        
        # Get package counts
        package_counts = {config: len(deps) for config, deps in self.dependencies.items()}
        
        # Get all unique packages
        all_packages = set()
        for deps in self.dependencies.values():
            all_packages.update(deps.keys())
            
        # Categorize packages
        categories = {
            'computer_vision': ['opencv-python', 'opencv-contrib-python', 'pillow', 'scikit-image', 'imageio'],
            'ml_ai': ['torch', 'transformers', 'google-generativeai', 'sentence-transformers'],
            'web_framework': ['flask', 'gradio', 'fastapi', 'django'],
            'data_processing': ['numpy', 'pandas', 'scipy'],
            'video_processing': ['moviepy', 'yt-dlp', 'pytube', 'ffmpeg-python'],
            'database': ['sqlalchemy', 'redis', 'psycopg2-binary', 'alembic'],
            'testing': ['pytest', 'pytest-cov', 'coverage'],
            'development': ['black', 'flake8', 'mypy']
        }
        
        categorized_packages = defaultdict(list)
        for package in all_packages:
            categorized = False
            for category, packages in categories.items():
                if package in packages:
                    categorized_packages[category].append(package)
                    categorized = True
                    break
            if not categorized:
                categorized_packages['other'].append(package)
        
        # Get import usage
        import_usage = self.analyze_import_usage()
        
        report = {
            'summary': {
                'total_unique_packages': len(all_packages),
                'configuration_counts': package_counts,
                'conflicts_found': len(self.conflicts),
                'security_issues': len(self.security_issues)
            },
            'configurations': self.dependencies,
            'conflicts': self.conflicts,
            'security_issues': self.security_issues,
            'categorized_packages': dict(categorized_packages),
            'import_usage': import_usage,
            'recommendations': self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Check for conflicts
        if self.conflicts:
            recommendations.append("🔧 Resolve version conflicts between requirement files")
            
        # Check for unused packages
        all_deps = set()
        for deps in self.dependencies.values():
            all_deps.update(deps.keys())
            
        import_usage = self.analyze_import_usage()
        potentially_unused = all_deps - set(import_usage.keys())
        
        if potentially_unused:
            recommendations.append(f"🧹 Review {len(potentially_unused)} potentially unused packages")
            
        # Security recommendations
        if self.security_issues:
            recommendations.append("🔒 Address security vulnerabilities in dependencies")
        else:
            recommendations.append("✅ No known security issues found")
            
        # General recommendations
        recommendations.extend([
            "📌 Pin exact versions for production deployment",
            "🐳 Use multi-stage Docker builds to reduce image size",
            "🔄 Implement automated dependency updates",
            "📊 Regular dependency audits and cleanup"
        ])
        
        return recommendations
    
    def save_report(self, output_file: str = "dependency_analysis.json"):
        """Save analysis report to JSON file"""
        report = self.generate_report()
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"📄 Report saved to {output_file}")
        return report

def main():
    """Main function to run dependency analysis"""
    print("🔍 Slide Extractor Dependency Analysis")
    print("=" * 50)
    
    analyzer = DependencyAnalyzer()
    
    # Run analysis
    analyzer.analyze_all_requirements()
    analyzer.find_conflicts()
    analyzer.check_security_vulnerabilities()
    
    # Generate and save report
    report = analyzer.save_report()
    
    # Print summary
    print(f"\n📊 Analysis Summary:")
    print(f"   Total unique packages: {report['summary']['total_unique_packages']}")
    print(f"   Configuration counts: {report['summary']['configuration_counts']}")
    print(f"   Conflicts found: {report['summary']['conflicts_found']}")
    print(f"   Security issues: {report['summary']['security_issues']}")
    
    print(f"\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    print(f"\n✅ Analysis complete! Check dependency_analysis.json for details.")

if __name__ == "__main__":
    main()
